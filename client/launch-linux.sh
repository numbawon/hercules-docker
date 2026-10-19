#!/bin/sh
# Start the Family RO client on a Linux desktop with a bigger UI.
#
# The client draws its windows at fixed pixel sizes, so on a 4K screen the UI
# is tiny whatever resolution you pick. This runs it inside gamescope at a
# lower "render" size and stretches that to your screen: --scale 3 on a
# 3840x2160 screen renders 1280x720, so everything looks three times as big.
#
#   ./launch-linux.sh [--dir ~/Games/FamilyRO] [--screen 3840x2160] [--scale 3] [--filter fsr]
#
# --filter is how the small picture is stretched: fsr (smooth, the default),
# pixel (sharp edges, best when the scale is a whole number), linear or nearest.
#
# Needs gamescope (Arch: sudo pacman -S gamescope) and wine. --scale 2 suits
# a 1080p screen, or 1.5 if 2 is too much (render size = screen / scale).
set -e
dir="$HOME/Games/FamilyRO"; screen="3840x2160"; scale="3"; filter="fsr"
while [ $# -gt 0 ]; do
    case "$1" in
        --dir) dir="$2"; shift 2 ;;
        --screen) screen="$2"; shift 2 ;;
        --scale) scale="$2"; shift 2 ;;
        --filter) filter="$2"; shift 2 ;;
        *) echo "unknown option $1"; exit 1 ;;
    esac
done
command -v gamescope >/dev/null || { echo "gamescope is not installed"; exit 1; }
sw=${screen%x*}; sh=${screen#*x}
rw=$(awk -v a="$sw" -v s="$scale" 'BEGIN { printf "%d", a / s }')
rh=$(awk -v a="$sh" -v s="$scale" 'BEGIN { printf "%d", a / s }')

# the client reads its resolution from savedata/OptionInfo.lua; make it match
# the render size and run fullscreen inside gamescope's own screen
opt="$dir/savedata/OptionInfo.lua"
if [ -f "$opt" ]; then
    sed -i -e "s/^OptionInfoList\[\"ISFULLSCREENMODE\"\] = .*/OptionInfoList[\"ISFULLSCREENMODE\"] = 1/" \
           -e "s/^OptionInfoList\[\"WIDTH\"\] = .*/OptionInfoList[\"WIDTH\"] = $rw/" \
           -e "s/^OptionInfoList\[\"HEIGHT\"\] = .*/OptionInfoList[\"HEIGHT\"] = $rh/" "$opt"
fi
cd "$dir"
exec gamescope -w "$rw" -h "$rh" -W "$sw" -H "$sh" -f -F "$filter" -- wine Ragexe_patched.exe
