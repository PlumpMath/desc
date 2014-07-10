import asyncio
import pickle

class requestManager(object):
    """ Server side class that listens for requests to render data to bam
        Should cooperate with another predictive class that generates related
        requests.

        This is the main code to handle all incomming request for a *single* session
        it itself can dispatch to multiple workers but there should only be one entry
        and one exit for a session, every new session gets its own instance of this?

        Yes, yes I know, http handles a lot of this stuff already, but we don't really
        need all those features.
    """
    def __init__(self,port):
        """ Set up to listen for requests for data from the render client.
            These requests will then spawn processes that retrieve and
            render the data and related data the user might want to view.
        """
        pass
    def listenForRequest(self):
        pass
    def handleRequest(self):
        pass

class connectionServerProtocol(asyncio.Protocol):
    """ Define the protocol for handling basic connections
        should spin up client specific connections?
    """
    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        #print('connection from: %s'%peername)
        print("connection from:",peername)
        self.transport = transport
        self.__receiving__ = False
        self.__block__ = b''

    def data_received(self, data):  # data is a bytes object
        print('data received: %s'%data)
        print([t for t in self.process_data(data)])
        #actually process the response
        self.transport.write(b'processed response')

    def process_data(self,data):
        #are we already receiving a stream?
            #new stream
                #what type of stream is it?
                #if the stream sends fixed sized requests just wait for bytes
            #existing stream
                #are we there yet?

        pickleStop = 0
        if not self.__receiving__:  #FIXME our pickle implementation needs to have a CLEAR stop opcode because . does not work :/
            pickleStart = data.find(b'\x80')
            if pickleStart != -1:
                pickleStop = data.find(b'..') + 1
                if not pickleStop:
                    pickleStop = -1  # it seems like there should be a cool way to exploit a failed find returning -1...
                self.__block__ += data[pickleStart:pickleStop]  # FIXME pickels should really come all at once but honestly no telling if the underlying implementation will accidentally chunk a pickle stream :/ need to test
        else:
            if self.__receiving__ == 'pickel':
                pickleStop = data.find(b'..') + 1
                if not pickleStop:
                    pickleStop = -1  # it seems like there should be a cool way to exploit a failed find returning -1...
                self.__block__ += data[pickleStart:pickleStop]

        if not pickleStop:
            self.__receiving__ = 'pickle'
            yield None
        else:  # make sure we don't have another pickle lurking in the rest of the data!
            thing = pickle.loads(self.__block__)
            self.__block__ = b''
            self.__receiving__ = False
            yield thing
            rest = data[pickeStop:]
            if len(rest) > 1:
                yield process_data(rest[1:])

                ##look for pickle end
            #else:
                #pass
                #look for newline or rather, just ignore it

    #def dispatch_block(self):
        #processBlock(self.transport,self.__block__)  # this should probably yield a future or something to keep it async




    def eof_received(self):
        #clean up the connection and store stuff because the client has exited
        print('got eof')
        pass
    

def main():
    serverLoop = asyncio.get_event_loop()
    coro_conServer = serverLoop.create_server(connectionServerProtocol, '127.0.0.1', 55555, ssl=None)  # TODO ssl
    server = serverLoop.run_until_complete(coro_conServer)
    try:
        serverLoop.run_forever()
    except KeyboardInterrupt:
        print('exiting...')
    finally:
        server.close()
        serverLoop.close()



if __name__ == "__main__":
    main()
