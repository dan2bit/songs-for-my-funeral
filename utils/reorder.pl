#!/usr/bin/env perl
# Songs for my Funeral — reorder script
# Renames mp3 and cover files on disk to match the current state of tracks.tsv.
#
# USE CASE: You've edited tracks.tsv — inserted, removed, or renumbered a
# track — and the filenames on disk are out of sync. Run this script to rename
# everything to match.
#
# HOW TO USE:
#   1. Edit tracks.tsv to reflect the desired state
#   2. perl reorder.pl          — dry run, shows what would be renamed
#   3. perl reorder.pl --apply  — actually renames the files
#   4. Run assemble.sh to rebuild the audio
#   5. Update liner-notes.html manually (track numbers don't auto-update)

use strict;
use warnings;
use File::Glob ':glob';
use Unicode::Normalize qw(NFC NFD);

my $apply = grep { $_ eq '--apply' } @ARGV;

unless ($apply) {
    print "\nDRY RUN — no files will be renamed.\n";
    print "Run with --apply to actually rename.\n\n";
}

# macOS HFS+ stores filenames in NFD (decomposed) form.
# tracks.tsv is likely NFC (composed). Normalize both to NFC for comparison,
# but use the raw on-disk name for the actual rename.

sub nfc_key {
    my $s = shift;
    # Decode raw bytes as UTF-8, normalize to NFC
    utf8::decode($s) unless utf8::is_utf8($s);
    return NFC($s);
}

# --- Read tracks.tsv ---
open my $fh, '<:encoding(UTF-8)', 'tracks.tsv' or die "Cannot open tracks.tsv: $!";
my @tracks;
while (<$fh>) {
    chomp;
    next if /^num\t/ or /^\s*$/ or /^#/;
    my ($num, $chapter, $filename, @rest) = split /\t/;
    push @tracks, { num => $num, filename => $filename };
}
close $fh;

# --- Build map of mp3s on disk: NFC(name_without_prefix) -> raw filename ---
my %disk_mp3;
for my $f (bsd_glob("*.mp3")) {
    if ($f =~ /^(\d+)\.\s+(.+)$/) {
        my $name = $2;
        $disk_mp3{ nfc_key($name) } = $f;  # key=NFC, value=raw on-disk name
    }
}

my ($mp3_renames, $mp3_skipped, $mp3_errors) = (0, 0, 0);

for my $t (@tracks) {
    my $target = $t->{filename};
    my ($name) = $target =~ /^\d+\.\s+(.+)$/;
    unless (defined $name) {
        print "  ✗ Cannot parse filename: $target\n";
        $mp3_errors++;
        next;
    }

    my $key = nfc_key($name);
    my $source = $disk_mp3{$key};
    unless (defined $source) {
        print "  ✗ NOT FOUND on disk: $name\n";
        $mp3_errors++;
        next;
    }

    # Compare NFC forms so accent normalization doesn't cause false mismatches
    if (nfc_key($source) eq nfc_key($target)) {
        $mp3_skipped++;
        next;
    }

    if ($apply) {
        rename($source, $target) or do {
            print "  ✗ FAILED: $source -> $target: $!\n";
            $mp3_errors++;
            next;
        };
        print "  ✓ $source\n    -> $target\n";
    } else {
        print "  -> $source\n    -> $target\n";
    }
    $mp3_renames++;
}

my $verb = $apply ? "renamed" : "would be renamed";
print "\n  mp3: $mp3_renames $verb, $mp3_skipped already correct, $mp3_errors error(s).\n";

# --- Cover renames ---
my ($cov_renames, $cov_skipped, $cov_missing) = (0, 0, 0);

for my $t (@tracks) {
    my $new_num = $t->{num};
    my ($old_num_raw) = $t->{filename} =~ /^(\d+)\./;
    my $old_num = sprintf("%02d", $old_num_raw);

    if ($old_num eq $new_num) {
        $cov_skipped++;
        next;
    }

    my $old_cover = (bsd_glob("covers/${old_num}-*.jpg"))[0];
    unless (defined $old_cover) {
        print "  ⚠ cover not found for track $old_num (not yet fetched — skipping)\n";
        $cov_missing++;
        next;
    }

    my ($slug) = $old_cover =~ m{covers/${old_num}-(.+)$};
    my $new_cover = "covers/${new_num}-${slug}";

    if ($old_cover eq $new_cover) {
        $cov_skipped++;
        next;
    }

    if ($apply) {
        rename($old_cover, $new_cover) or do {
            print "  ✗ FAILED: $old_cover -> $new_cover: $!\n";
            next;
        };
        print "  ✓ $old_cover\n    -> $new_cover\n";
    } else {
        print "  -> $old_cover\n    -> $new_cover\n";
    }
    $cov_renames++;
}

$verb = $apply ? "renamed" : "would be renamed";
print "\n  covers: $cov_renames $verb, $cov_skipped already correct, $cov_missing not yet fetched.\n";

if (!$apply && ($mp3_renames + $cov_renames) > 0) {
    print "\n  Run with --apply to execute.\n";
}

if ($mp3_errors > 0) {
    print "\n  Fix missing files before running --apply.\n";
    exit 1;
}

print "\n";
