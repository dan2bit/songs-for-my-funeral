#!/bin/bash
# Songs for my Funeral — ffmpeg assembly script
# Driven by tracks.tsv — edit that file to change order, transitions, chapters.
# Run from the directory containing your mp3 files and tracks.tsv.
# Requires ffmpeg: brew install ffmpeg
#
# tracks.tsv columns (tab-separated):
#   num  chapter  filename  transition_type  transition_secs  chapter_break_after
#
# transition_type:
#   gap    = silence inserted after this track
#   xfade  = crossfade into the NEXT track (they must be consecutive xfades or
#             the last in a chain must be followed by gap/end)
#   end    = last track, no transition
#
# chapter_break_after:
#   yes    = insert 3.5s chapter gap after this track's transition
#            (the transition_secs on this row is the within-chapter gap
#             before the chapter break, so usually 0 or absent — but if
#             non-zero it adds silence before the chapter break too)
#   (blank) = normal within-chapter transition

set -e


TSV="tracks.tsv"

if [ ! -f "$TSV" ]; then
  echo "ERROR: $TSV not found. Run from the directory containing tracks.tsv."
  exit 1
fi

# ─────────────────────────────────────────────────────
# Duration check helper
# ─────────────────────────────────────────────────────
check_duration() {
  local file="$1"
  local expected_secs="$2"
  local label="$3"
  local actual
  actual=$(ffprobe -v error -show_entries format=duration \
    -of default=noprint_wrappers=1:nokey=1 "$file")
  local actual_int=${actual%.*}
  local mins=$((actual_int / 60))
  local secs=$((actual_int % 60))
  local diff=$(echo "$actual - $expected_secs" | bc)
  local abs_diff=${diff#-}
  local status="✓"
  if (( $(echo "$abs_diff > 10" | bc -l) )); then
    status="⚠️  UNEXPECTED"
  fi
  printf "  %s  %-52s %d:%02d  (expected ~%d:%02d)\n" \
    "$status" "$label" $mins $secs \
    $(( expected_secs / 60 )) $(( expected_secs % 60 ))
}

# ─────────────────────────────────────────────────────
# STEP 1: Generate silence files
# ─────────────────────────────────────────────────────

# Collect all unique gap durations needed (including chapter break 3.5s)
SILENCE_DURATIONS=()
while IFS=$'\t' read -r num chapter filename ttype tsecs chbreak || [ -n "$num" ]; do
  [[ "$num" =~ ^#.*$ || -z "$num" || "$num" = "num" ]] && continue
  if [ "$ttype" = "gap" ] && [ -n "$tsecs" ] && [ "$tsecs" != "0" ]; then
    SILENCE_DURATIONS+=("$tsecs")
  fi
  if [ "$chbreak" = "yes" ]; then
    SILENCE_DURATIONS+=("3.5")
  fi
done < "$TSV"

# Deduplicate
IFS=$'\n' UNIQUE_SILENCES=($(printf '%s\n' "${SILENCE_DURATIONS[@]}" | sort -u))
unset IFS

for dur in "${UNIQUE_SILENCES[@]}"; do
  ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=stereo \
    -t "$dur" "silence_${dur}s.mp3" 2>/dev/null
done

# ─────────────────────────────────────────────────────
# STEP 2: Read tracks into arrays
# ─────────────────────────────────────────────────────

declare -a T_NUM T_CHAPTER T_FILE T_TYPE T_SECS T_BREAK

i=0
while IFS=$'\t' read -r num chapter filename ttype tsecs chbreak || [ -n "$num" ]; do
  [[ "$num" =~ ^#.*$ || -z "$num" || "$num" = "num" ]] && continue
  T_NUM[$i]="$num"
  T_CHAPTER[$i]="$chapter"
  T_FILE[$i]="$filename"
  T_TYPE[$i]="$ttype"
  T_SECS[$i]="$tsecs"
  T_BREAK[$i]="$chbreak"
  (( i++ )) || true
done < "$TSV"

TOTAL=${#T_NUM[@]}

# ─────────────────────────────────────────────────────
# STEP 3: Build chapter files
# ─────────────────────────────────────────────────────

# Find unique chapters
CHAPTERS=($(printf '%s\n' "${T_CHAPTER[@]}" | sort -u -n))

CHAPTER_FILES=()
CHAPTER_LABELS=(
  [1]="I Am Where I'm Meant to Be"
  [2]="You'll Be Okay (Grief Sucks)"
  [3]="Don't Worry About Me"
  [4]="You're Still in the Pink"
  [5]="But Before We Part"
  [6]="Go in Good Graces"
)
CHAPTER_EXPECTED=(
  [1]=822
  [2]=1733
  [3]=754
  [4]=1714
  [5]=1374
  [6]=661
)
CHAPTER_SLUGS=(
  [1]="i-am-where-im-meant-to-be"
  [2]="youll-be-okay"
  [3]="dont-worry-about-me"
  [4]="youre-still-in-the-pink"
  [5]="but-before-we-part"
  [6]="go-in-good-graces"
)

for ch in "${CHAPTERS[@]}"; do
  # Collect indices for this chapter
  CH_IDX=()
  for (( j=0; j<TOTAL; j++ )); do
    [ "${T_CHAPTER[$j]}" = "$ch" ] && CH_IDX+=($j)
  done

  CHFILE="chapter-$(printf '%02d' $ch)-${CHAPTER_SLUGS[$ch]}.mp3"

  # ── Identify xfade chains in this chapter ──
  # We process the chapter left to right. When we hit an xfade, we collect
  # the run of consecutive xfades and the track immediately after them,
  # build a single acrossfade chain, write to a temp file, and treat that
  # temp file as a single item in the concat list.

  CONCAT_ITEMS=()   # list of filenames to concat (gaps + xfade-chain outputs)
  TEMP_FILES=()     # track temp files to clean up
  NEEDS_REENCODE=0  # if any xfade exists, we must re-encode at concat

  k=0
  while [ $k -lt ${#CH_IDX[@]} ]; do
    idx=${CH_IDX[$k]}
    ttype="${T_TYPE[$idx]}"

    if [ "$ttype" = "xfade" ]; then
      # Collect the xfade chain: this track + all following xfade tracks + one more
      CHAIN_IDX=($idx)
      kk=$(( k + 1 ))
      while [ $kk -lt ${#CH_IDX[@]} ]; do
        next_idx=${CH_IDX[$kk]}
        CHAIN_IDX+=($next_idx)
        if [ "${T_TYPE[$next_idx]}" != "xfade" ]; then
          break
        fi
        (( kk++ )) || true
      done

      # Build acrossfade filter for chain
      # Chain length = ${#CHAIN_IDX[@]} tracks
      CHAIN_LEN=${#CHAIN_IDX[@]}
      FFMPEG_INPUTS=()
      for ci in "${CHAIN_IDX[@]}"; do
        FFMPEG_INPUTS+=(-i "${T_FILE[$ci]}")
      done

      # Build filter_complex string
      FILTER=""
      for (( fi=0; fi < CHAIN_LEN - 1; fi++ )); do
        src_idx=${CHAIN_IDX[$fi]}
        xsecs="${T_SECS[$src_idx]}"
        if [ $fi -eq 0 ]; then
          in_a="[0:a]"
          in_b="[1:a]"
        else
          in_a="[a$(printf '%03d' $fi)]"
          in_b="[$(( fi + 1 )):a]"
        fi
        if [ $fi -eq $(( CHAIN_LEN - 2 )) ]; then
          out_label="[out]"
        else
          out_label="[a$(printf '%03d' $(( fi + 1 )))]"
        fi
        FILTER+="${in_a}${in_b}acrossfade=d=${xsecs}:c1=tri:c2=tri${out_label};"
      done
      FILTER="${FILTER%;}"  # trim trailing semicolon

      TMPFILE="_xfade_ch${ch}_${k}.mp3"
      ffmpeg -y "${FFMPEG_INPUTS[@]}" \
        -filter_complex "$FILTER" \
        -map "[out]" -q:a 0 "$TMPFILE"

      CONCAT_ITEMS+=("$TMPFILE")
      TEMP_FILES+=("$TMPFILE")
      NEEDS_REENCODE=1

      # The last track in chain: if it has a gap after it (not end/xfade),
      # add that silence now
      last_chain_idx=${CHAIN_IDX[$(( ${#CHAIN_IDX[@]} - 1 ))]}
      last_type="${T_TYPE[$last_chain_idx]}"
      last_secs="${T_SECS[$last_chain_idx]}"
      if [ "$last_type" = "gap" ] && [ -n "$last_secs" ] && [ "$last_secs" != "0" ]; then
        CONCAT_ITEMS+=("silence_${last_secs}s.mp3")
      fi

      k=$(( kk + 1 ))

    elif [ "$ttype" = "gap" ]; then
      CONCAT_ITEMS+=("${T_FILE[$idx]}")
      tsecs="${T_SECS[$idx]}"
      if [ -n "$tsecs" ] && [ "$tsecs" != "0" ]; then
        CONCAT_ITEMS+=("silence_${tsecs}s.mp3")
      fi
      (( k++ )) || true

    else
      # end
      CONCAT_ITEMS+=("${T_FILE[$idx]}")
      (( k++ )) || true
    fi
  done

  # Write concat list
  LISTFILE="_chapter${ch}_list.txt"
  > "$LISTFILE"
  for item in "${CONCAT_ITEMS[@]}"; do
    _e=$(echo "$item" | sed "s/'/'\\\\''/g") ; echo "file '$_e'" >> "$LISTFILE"
  done

  if [ "$NEEDS_REENCODE" -eq 1 ]; then
    ffmpeg -y -f concat -safe 0 -i "$LISTFILE" -q:a 0 "$CHFILE"
  else
    ffmpeg -y -f concat -safe 0 -i "$LISTFILE" -c copy "$CHFILE"
  fi

  rm "$LISTFILE"
  for tf in "${TEMP_FILES[@]}"; do rm -f "$tf"; done

  CHAPTER_FILES+=("$CHFILE")
  check_duration "$CHFILE" "${CHAPTER_EXPECTED[$ch]}" \
    "Chapter $ch: ${CHAPTER_LABELS[$ch]}"
done

# ─────────────────────────────────────────────────────
# STEP 4: Concatenate chapters into master file
# 3.5s gap between each chapter
# ─────────────────────────────────────────────────────

> _master_list.txt
for (( m=0; m<${#CHAPTER_FILES[@]}; m++ )); do
  _e=$(echo "${CHAPTER_FILES[$m]}" | sed "s/'/'\\\\''/g") ; echo "file '$_e'" >> _master_list.txt
  if [ $m -lt $(( ${#CHAPTER_FILES[@]} - 1 )) ]; then
    echo "file 'silence_3.5s.mp3'" >> _master_list.txt
  fi
done

ffmpeg -y -f concat -safe 0 -i _master_list.txt \
  -q:a 0 "songs-for-my-funeral.mp3"
rm _master_list.txt

# ─────────────────────────────────────────────────────
# STEP 5: Clean up silence files
# ─────────────────────────────────────────────────────

for dur in "${UNIQUE_SILENCES[@]}"; do
  rm -f "silence_${dur}s.mp3"
done

echo ""
echo "Chapter durations:"
for chfile in "${CHAPTER_FILES[@]}"; do
  ch_num=$(echo "$chfile" | grep -o 'chapter-[0-9][0-9]' | grep -o '[0-9]*$' | sed 's/^0//')
  check_duration "$chfile" "${CHAPTER_EXPECTED[$ch_num]}" \
    "Chapter $ch_num: ${CHAPTER_LABELS[$ch_num]}"
done
echo ""
check_duration "songs-for-my-funeral.mp3" 7099 "Master: Songs for my Funeral"
echo ""
