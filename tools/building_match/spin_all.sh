cd /tmp/claude-0/buildW/bin
export DISPLAY=:99 SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1 MESA_GL_VERSION_OVERRIDE=3.3 MESA_GLSL_VERSION_OVERRIDE=330 AC_MV_DIST=1.55 AC_MV_SPIN=16
for i in 0 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30 32 34 36 38 42 44; do
  D=/tmp/claude-0/acb/$i; mkdir -p $D
  AC_MV_SPIN_DIR=$D timeout -s KILL 120 ./AnimalCrossing --model-viewer $i > /dev/null 2>&1
done
echo SPINALL > /tmp/claude-0/spin_all_done
