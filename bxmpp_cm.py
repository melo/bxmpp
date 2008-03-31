"""
Binary XMPP Connection Manager - Twisted Version
http://www.xmpp.org/extensions/binary-xmpp.html
Usage: python bxmpp_cm.py jabberhost
"""

from twisted.internet import reactor, protocol

debug = True

class VerboseClient(protocol.Protocol):
    """
    Connecting to the Jabber server using the verbose XML encoding
    """

    def __init__(self, parent):
        self.parent = parent

    def connectionMade(self):
        self.parent.clientConnected(self)

    def connectionLost(self, reason):
        self.parent.clientLost()
    
    def dataReceived(self, data):
        self.parent.clientDataReceived(data)

    def write(self, data):
        self.transport.write(data)


class BXMPP(protocol.Protocol):
    """
    Connection manager supporting the optimized, highly compressible Binary XMPP
    """

    def connectionMade(self):
        cc = protocol.ClientCreator(reactor, VerboseClient, self)
        cc.connectTCP(self.factory.verbose_host, 5222)
        # BXMPP 2.0 ready: uncomment this!
        #self.transport.write("<bxmpp lang=\"en\">")
        self.buf = ""
        self.opening_received = False
        self.cbyte = 0
        self.cbytepos = 0
        self.verbose_client = None

    def dataReceived(self, data):
        self.buf += data
        # BXMPP 2.0 ready: uncomment these lines!
        #if not self.opening_received and  self.buf.find("<bxmpp lang=\"en\">") == 0:
        #        self.opening_received = True
        #        self.buf = self.buf[len("<bxmpp lang=\"en\">"):]
        self.sendVerboseData()
    
    def sendVerboseData(self):
        if not self.verbose_client: return
        while True:
            one = self.buf.find("<one />") == 0
            zero = self.buf.find("<zero />") == 0
            if one:
                bit = 1
                self.buf = self.buf[len("<one />"):]
            elif zero:
                bit = 0
                self.buf = self.buf[len("<zero />"):]
            else:
                break
            self.cbyte |= bit << self.cbytepos
            self.cbytepos += 1
            if self.cbytepos == 8:
                self.verbose_client.write(chr(self.cbyte))
                self.cbyte = 0
                self.cbytepos = 0

    def clientDataReceived(self, data):
        for c in data:
            c = ord(c)
            for i in range(8):
                b = c & 0x01
                if b: self.transport.write("<one />")
                else: self.transport.write("<zero />")
                c >>= 1

    def clientConnected(self, client):
        self.verbose_client = client
        self.sendVerboseData()

    def clientLost(self):
        self.verbose_client = None
        self.transport.write("</bxmpp>")
        self.transport.loseConnection()
    
    def connectionLost(self, reason):
        if self.verbose_client:
            self.verbose_client.transport.loseConnection()

if __name__ == "__main__":
    import sys
    f = protocol.ServerFactory()
    f.protocol = BXMPP
    f.verbose_host = sys.argv[1]
    reactor.listenTCP(10110, f)
    reactor.run()
