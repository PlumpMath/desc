#!/usr/bin/env python3.4


import ssl
import time
from asyncio import get_event_loop
from threading import Thread

from IPython import embed

#import rpdb2
#rpdb2.start_embedded_debugger("asdf123")
#rpdb2.settrace()


# XXX NOTE TODO: There are "DistributedObjects" that exist in panda3d that we might be able to use instead of this???
    #that would vastly simplify life...? ehhhhh

def startup():
    return "starting"

def main():
    import sys
    from concurrent.futures import ProcessPoolExecutor

    # render setup
    from direct.showbase.ShowBase import ShowBase
    from panda3d.core import loadPrcFileData
    from panda3d.core import PStatClient

    from render_manager import renderManager
    from selection import BoxSel
    from util import ui_text, console, exit_cleanup, frame_rate, startup_data
    from ui import CameraControl, Axis3d, Grid3d, GuiFrame
    from protocols import dataClientProtocol

    # fix sys module reference
    sys.modules['core'] = sys.modules['panda3d.core']

    PStatClient.connect() #run pstats in console
    loadPrcFileData('','view-frustum-cull 0')
    base = ShowBase()

    base.setBackgroundColor(0,0,0)
    base.disableMouse()
    # TODO init all these into a dict or summat?
    startup_data()
    frame_rate()
    ut = ui_text()
    grid = Grid3d()
    axis = Axis3d()
    cc = CameraControl()
    con = console()

    # TODO make it so that all the "root" nodes for the secen are initialized in their own space, probably in with defaults or something globalValues.py?
    # roots

    # frames XXX FIXME TODO this is a terrible way to pass this around...
    frames = {
        'data':GuiFrame('Data view')
    }

    #asyncio and network setup
    clientLoop = get_event_loop()
    ppe = ProcessPoolExecutor()
    #startup = lambda: "STARTING"
    out = ppe.submit(startup)  # FIXME WAT WAT WAT mega bug with starting the process pool for the first time in run_in_executor, something with future state = running
    print(out)
    #clientLoop.set_default_executor(ppe)

    #make sure we can exit
    el = exit_cleanup(clientLoop, ppe)  #use this to call stop() on run_forever

    rendMan = renderManager(clientLoop, ppe)

    bs = BoxSel(frames)

    # TODO ssl contexts
    conContext = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cadata=None)  # TODO cadata should allow ONLY our self signed, severly annoying to develop...
    dataContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)

    #datCli_base = type('dataClientProtocol',(dataClientProtocol,),
                  #{'set_nodes':rendMan.set_nodes,  # FIXME this needs to go through make_nodes
                   #'render_set_send_request':rendMan.set_send_request,
                   #'cache':rendMan.cache,
                   #'event_loop':clientLoop })  # FIXME we could move event_loop to __new__? 

    datCli_base = dataClientProtocol(rendMan.set_nodes, rendMan.set_send_request, rendMan.cache, clientLoop)
    datCli = datCli_base()
    datCli.connection_lost('START')

    asyncThread = Thread(target=clientLoop.run_forever)
    asyncThread.start()
    run()  # this MUST be called last because we use sys.exit() to terminate
    assert False, 'Note how this never gets printed due to sys.exit()'


if __name__ == "__main__":
    #for _ in range(10):
    main()
