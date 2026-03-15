#!/bin/bash
# duration.sh
# Calculates total runtime of all tracks plus all transition gaps/crossfades.
# Reads transition values from tracks.tsv — no hardcoded durations.
# Run from the folder containing your mp3 files and tracks.tsv.
# Requires ffmpeg.

TSV="tracks.tsv"

if [ ! -f "$TSV" ]; then
  echo "ERROR: $TSV not found. Run from the directory containing tracks.tsv."
  exit 1
fi

echo ""
echo "Track durations"
echo "─────────────────────────────────────────────────────────────────"
printf "%-6s %-12s %s\n" "Track" "Duration" "File"
echo "─────────────────────────────────────────────────────────────────"

TOTAL_SECONDS=0
TRANSITION_SECS=0
TRANSITION_EXPR=""

while IFS=$'\t' read -r num chapter filename ttype tsecs chbreak || [ -n "$num" ]; do
  [[ "$num" =~ ^#.*$ || -z "$num" || "$num" = "num" ]] && continue

  # Track duration
  if [ -f "$filename" ]; then
    SECS=$(ffprobe -v error -show_entries format=duration \
      -of default=noprint_wrappers=1:nokey=1 "$filename" 2>/dev/null)
    INT=${SECS%.*}
    MINS=$((INT / 60))
    SECS_PART=$((INT % 60))
    FORMATTED=$(printf "%d:%02d" $MINS $SECS_PART)
    printf "%-6s %-12s %s\n" "$num" "$FORMATTED" "$filename"
    TOTAL_SECONDS=$(echo "$TOTAL_SECONDS + $SECS" | bc)
  else
    printf "%-6s %-12s %s\n" "$num" "MISSING" "$filename"
  fi

  # Accumulate transition time
  # xfades: the crossfade duration is an *overlap*, not added silence —
  # net effect on total time is the same as a gap of that duration
  # (both cases: we add the seconds to total)
  if [ "$ttype" = "gap" ] || [ "$ttype" = "xfade" ]; then
    if [ -n "$tsecs" ] && [ "$tsecs" != "0" ]; then
      TRANSITION_SECS=$(echo "$TRANSITION_SECS + $tsecs" | bc)
      TRANSITION_EXPR="${TRANSITION_EXPR}+${tsecs}"
    fi
  fi

  # Chapter break adds 3.5s (the chapter gap is always 3.5s)
  if [ "$chbreak" = "yes" ]; then
    TRANSITION_SECS=$(echo "$TRANSITION_SECS + 3.5" | bc)
    TRANSITION_EXPR="${TRANSITION_EXPR}+3.5(chbreak)"
  fi

done < "$TSV"

echo "─────────────────────────────────────────────────────────────────"

# Format helper
format_duration() {
  local total=$1
  local int=${total%.*}
  local h=$((int / 3600))
  local m=$(( (int % 3600) / 60 ))
  local s=$((int % 60))
  if [ "$h" -gt 0 ]; then
    printf "%d:%02d:%02d" $h $m $s
  else
    printf "%d:%02d" $m $s
  fi
}

floor_bc() { echo "${1%.*}"; }

GRAND_TOTAL=$(echo "$TOTAL_SECONDS + $TRANSITION_SECS" | bc)

TRACK_FMT=$(format_duration $(floor_bc $TOTAL_SECONDS))
TRANS_FMT=$(format_duration $(floor_bc $TRANSITION_SECS))
GRAND_FMT=$(format_duration $(floor_bc $GRAND_TOTAL))

# ─────────────────────────────────────────────────────
# Chapter and master files (if present)
# ─────────────────────────────────────────────────────

CHAPTER_FILES=(
  "chapter-01-i-am-where-im-meant-to-be.mp3|Chapter 1: I Am Where I'm Meant to Be|822"
  "chapter-02-youll-be-okay.mp3|Chapter 2: You'll Be Okay (Grief Sucks)|1733"
  "chapter-03-dont-worry-about-me.mp3|Chapter 3: Don't Worry About Me|754"
  "chapter-04-youre-still-in-the-pink.mp3|Chapter 4: You're Still in the Pink|1391"
  "chapter-05-but-before-we-part.mp3|Chapter 5: But Before We Part|1374"
  "chapter-06-go-in-good-graces.mp3|Chapter 6: Go in Good Graces|661"
  "songs-for-my-funeral.mp3|Master: Songs for my Funeral|6754"
)

FOUND_ANY=0
for entry in "${CHAPTER_FILES[@]}"; do
  file="${entry%%|*}"
  rest="${entry#*|}"
  label="${rest%%|*}"
  expected="${rest##*|}"

  if [ -f "$file" ]; then
    if [ "$FOUND_ANY" -eq 0 ]; then
      echo ""
      echo "Chapter and master files"
      echo "─────────────────────────────────────────────────────────────────"
      printf "%-10s %-10s %-52s %s\n" "Actual" "Expected" "File" "Status"
      echo "─────────────────────────────────────────────────────────────────"
      FOUND_ANY=1
    fi

    SECS=$(ffprobe -v error -show_entries format=duration \
      -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null)
    INT=${SECS%.*}
    MINS=$((INT / 60))
    SECS_PART=$((INT % 60))
    ACTUAL_FMT=$(printf "%d:%02d" $MINS $SECS_PART)

    EXP_MINS=$((expected / 60))
    EXP_SECS=$((expected % 60))
    EXP_FMT=$(printf "%d:%02d" $EXP_MINS $EXP_SECS)

    DIFF=$(echo "$SECS - $expected" | bc)
    ABS_DIFF=${DIFF#-}
    if (( $(echo "$ABS_DIFF > 10" | bc -l) )); then
      STATUS="⚠️  UNEXPECTED"
    else
      STATUS="✓"
    fi

    printf "%-10s %-10s %-52s %s\n" "$ACTUAL_FMT" "~$EXP_FMT" "$label" "$STATUS"
  fi
done

if [ "$FOUND_ANY" -eq 1 ]; then
  echo "─────────────────────────────────────────────────────────────────"
  echo ""
fi

printf "%-24s %s\n" "Tracks only:" "$TRACK_FMT"
printf "%-24s %s\n" "Transitions:" "$TRANS_FMT"
printf "%-24s %s\n" "Total runtime:" "$GRAND_FMT"
echo ""
