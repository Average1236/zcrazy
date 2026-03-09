from PyQt6.QtNetwork import QUdpSocket, QHostAddress, QAbstractSocket
from PyQt6.QtCore import QObject, pyqtSignal

class QtMulticastReceiver(QObject):
    dataReceived = pyqtSignal(bytes, str) # payload, ip

    def __init__(self, multicast_ip, port, parent=None):
        super().__init__(parent)
        self.socket = QUdpSocket(self)
        # Bind using ShareAddress and ReuseAddressHint to act similarly to SO_REUSEADDR
        self.socket.bind(QHostAddress.SpecialAddress.AnyIPv4, port, 
                         QAbstractSocket.BindFlag.ShareAddress | QAbstractSocket.BindFlag.ReuseAddressHint)
        self.socket.joinMulticastGroup(QHostAddress(multicast_ip))
        self.socket.readyRead.connect(self.readPendingDatagrams)

    def readPendingDatagrams(self):
        while self.socket.hasPendingDatagrams():
            datagram, host, port = self.socket.readDatagram(self.socket.pendingDatagramSize())
            ip_str = host.toString()
            if ip_str.startswith("::ffff:"):
                ip_str = ip_str[7:]
            self.dataReceived.emit(datagram, ip_str)

class QtPointToPointReceiver(QObject):
    dataReceived = pyqtSignal(bytes, str) # payload, ip

    def __init__(self, local_ip, port, parent=None):
        super().__init__(parent)
        self.socket = QUdpSocket(self)
        self.target_ip = None
        self.receive_flag = False
        self.socket.bind(QHostAddress.SpecialAddress.AnyIPv4, port, QAbstractSocket.BindFlag.ShareAddress | QAbstractSocket.BindFlag.ReuseAddressHint)
        self.socket.readyRead.connect(self.readPendingDatagrams)

    def readPendingDatagrams(self):
        while self.socket.hasPendingDatagrams():
            datagram, host, port = self.socket.readDatagram(self.socket.pendingDatagramSize())
            if not self.receive_flag:
                continue

            host_str = host.toString()
            if host_str.startswith("::ffff:"):
                host_str = host_str[7:]
            
            target = self.target_ip
            if target and target.startswith("::ffff:"):
                target = target[7:]

            if self.target_ip is None or host_str == target:
                self.dataReceived.emit(datagram, host_str)


class QtUdpSender(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.socket = QUdpSocket(self)

    def send(self, msg, ip, port):
        self.socket.writeDatagram(msg, QHostAddress(ip), port)
