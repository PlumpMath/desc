#so it looks like it is possible to stream stuff in using multifiles in pand3d
#obviously in the long run we will probably want our own optimized renderer
#but this is somehwere to start
#install is a freeking mess

#must install with --no-ode because there is some weird error with python3.4
#not sure why... it works fine on athena


#utf-8 decoding problems somehwere... looks like it is in core.NodePath
#rebuild with symbols optimize=0
#FOUND YOU! tis in incremental/panda/src/pgraph/nodePath.cxx
    #actually in nodePath.h under get_tag



"""
must ./configure --enable-shared when building python
in order to actually get panda3d to find the bloody Python.h and libpython3.4 we need to???
    modify makepandacore.py (there is probably somewhere correct to do this)
    ~ MUST be the full path written out eg /home/tgillesp
    add ~/.local/include to INCDIRECTORIES 2172
    add ~/.local/lib to LIBDIRECTORIES 2173
python makepanda/makepanda.py --everything --threads 8 --optimize 3 --verbose --no-od
python makepanda/installpanda.py --destdir=/home/tgillesp/.local/ --prefix=/
The right way to do this is as follows:
1) run makepanda/makepanda.py with the version of python you want panda3d to use
2) run python makepanda/installpanda.py --destdir=/home/user/.local/ --prefix=/
3) add /home/user/.local/lib64/panda3d to LD_LIBRARY_PATH
un needed
#export PYTHONPATH=$PYTHONPATH:~/.local/share/panda3d/direct:~/.local/share/panda3d/pandac
"""
