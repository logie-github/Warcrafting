cd /tmp/claude-0/buildW/bin
export DISPLAY=:99 SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1 MESA_GL_VERSION_OVERRIDE=3.3 MESA_GLSL_VERSION_OVERRIDE=330 AC_MV_SPIN=16 AC_MV_DIST=1.55
for pair in 2:70 4:75 6:75 26:80 28:80 30:80 44:70; do
  i=${pair%%:*}; f=${pair##*:}
  D=/tmp/claude-0/acb/$i; mkdir -p $D
  AC_MV_FOV=$f AC_MV_SPIN_DIR=$D timeout -s KILL 120 ./AnimalCrossing --model-viewer $i > /dev/null 2>&1
done
echo FIX > /tmp/claude-0/spin_fix_done
