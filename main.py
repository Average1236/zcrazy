# udp receiver for multicast
import os
import sys, socket, threading
from PyQt6.QtGui import QFont, QPainter, QColor, QImage, QMouseEvent, QPen
from PyQt6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PyQt6.QtQuick import QQuickPaintedItem
from PyQt6.QtCore import Qt,QRectF,QRect,QSize,pyqtSlot,pyqtSignal,QTimer
from PyQt6.QtCore import pyqtProperty

from PyQt6.QtWidgets import  QApplication

import pyqtgraph as pg

import zss_cmd_pb2 as zss
import zss_cmd_type_pb2 as zss_type

import network
from datetime import datetime

fdbNeedPlotName = []
refNeedPlotName = []
fdbPlotForward = "info."
refPlotForward = "self.pb_data."
    
needPlot = True
# plotDataNum = 0
# plotInitFinish = False

# plotData = [0]*plotDataNum
# plotDataList = [[] for _ in range(plotDataNum)]

onlineLock = threading.Lock()
changeSendTick = 0
changeSendTickLock = threading.Lock()

ipForward = "192.168.31"

onlineTick = [0]*32

MC_ADDR = "225.225.225.225"
MC_PORT = 13134
SEND_PORT = 14234
SINGLE_PORT = 14134


def resource_path(rel_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel_path)
    return os.path.join(os.path.abspath("."), rel_path)

# udp receiver for multicast
def get_ip_address():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return ip_address

local_ip=get_ip_address()
print("本机IP地址是:", local_ip)
class InfoReceiver:
    info = {}
    selected = {}
    def __init__(self,info_cb = None):
        self.info = {}
        self.info_cb = info_cb
    def _cb(self,data,addr):
        pb_info = zss.Multicast_Status()
        pb_info.ParseFromString(data)
        pb_info.ip = int(addr.split(".")[3])
        self.info[addr] = pb_info  
        if self.info_cb is not None:
            self.info_cb(pb_info.robot_id,pb_info)
                     
class CmdSender:
    def __init__(self):
        self.udpSender = network.QtUdpSender()
        self.pb_data = zss.Robot_Command()
        self.pb_data.robot_id = -1
        self.pb_data.kick_mode = zss.Robot_Command.KickMode.NONE
        # self.pb_data.desire_power = power
        self.pb_data.kick_discharge_time = 0
        self.pb_data.dribble_spin = 0
        self.pb_data.cmd_type = zss.Robot_Command.CmdType.CMD_VEL
        self.pb_data.cmd_vel.velocity_x = int(0*1000)
        self.pb_data.cmd_vel.velocity_y = int(0*1000)
        self.pb_data.cmd_vel.velocity_r = int(0*1000)
        self.pb_data.cmd_vel.use_imu = False
        self.pb_data.cmd_vel.imu_theta = int(0*3.1415926/180.0*1000)
        self.pb_data.comm_type = zss.Robot_Command.CommType.UDP_WIFI
        self.pb_data.angle_pid.append(int(6.5*1000))
        self.pb_data.angle_pid.append(int(0*1000))
        self.pb_data.angle_pid.append(int(0.8*1000))
        self.pb_data.need_change_team = False
        self.pb_data.need_change_id = False
        self.pb_data.team_new = zss.Team.UNKNOWN
        self.pb_data.id_new = -1
        self.pb_data.isdebug = True
        pass
    # updateCommandParams(int robotID,double velX,double velY,double velR,double ctrl,bool mode,bool shoot,double power)
    # 在UI.qml中调用来传递控制指令
    def updateCommandParams(self,robotID,velX,velY,velR,ctrl,mode,shoot,power,use_imu,angle):
        # self.pb_data = zss.Robot_Command()
        self.pb_data.robot_id = -1
        self.pb_data.kick_mode = zss.Robot_Command.KickMode.NONE if not shoot else (zss.Robot_Command.KickMode.CHIP if mode else zss.Robot_Command.KickMode.KICK)
        # self.pb_data.desire_power = power
        self.pb_data.kick_discharge_time = int(power)
        # print(power)
        self.pb_data.dribble_spin = int(ctrl)
        self.pb_data.cmd_type = zss.Robot_Command.CmdType.CMD_VEL
        self.pb_data.cmd_vel.velocity_x = int(velX*1000.0)
        self.pb_data.cmd_vel.velocity_y = int(velY*1000.0)
        if use_imu:
            self.pb_data.cmd_vel.velocity_r = int(angle*3.1415926/180.0*1000.0)
            self.pb_data.cmd_vel.imu_theta = int(angle*3.1415926/180.0*1000)
        else:
            self.pb_data.cmd_vel.velocity_r = int(velR*1000.0)
        self.pb_data.cmd_vel.use_imu = use_imu
        # self.pb_data.cmd_vel.imu_theta = angle*3.1415926/180.0
        self.pb_data.comm_type = zss.Robot_Command.CommType.UDP_WIFI
        self.pb_data.angle_pid.clear()
        self.pb_data.angle_pid.append(int(6.5*1000.0))
        self.pb_data.angle_pid.append(int(0*1000.0))
        self.pb_data.angle_pid.append(int(0.5*1000.0))
        self.pb_data.wheel_pid.clear()
        self.pb_data.wheel_pid.append(int(0.1*1000.0))
        self.pb_data.wheel_pid.append(int(0.6*1000.0))
        self.pb_data.wheel_pid.append(int(0*1000.0))
        self.pb_data.isdebug = True
          
    def changeTeam(self, team_new):
        self.pb_data.need_change_team = True
        self.pb_data.team_new = team_new
        global changeSendTick
        changeSendTick = 0

    def changeId(self, id_new):
        self.pb_data.need_change_id = True
        self.pb_data.id_new = id_new
        global changeSendTick
        changeSendTick = 0

    def sendCommand(self,infoReceiver:InfoReceiver):
        # print("sendCommand",str(self.pb_data))
        global changeSendTick
        if self.pb_data.need_change_team or self.pb_data.need_change_id:
            changeSendTick += 1
            if changeSendTick >= 5:
                self.pb_data.need_change_team = False
                self.pb_data.need_change_id = False
                    
        # print("debug")
        selectedDir = infoReceiver.selected
        global ipForward 
        ipForward_t = ipForward
        for id,info in selectedDir.items():
            
            global plotData
            global plotInitFinish

            if plotInitFinish: 
                for i in range(len(refNeedPlotName)):
                    plotData[i+len(fdbNeedPlotName)] = eval(refNeedPlotName[i])
              
            self.pb_data.robot_id = id
            # print("sendIp: ",info.ip)
            # Serialize    
            # print("send",self.pb_data.need_change_team, self.pb_data.need_change_id)
            data = self.pb_data.SerializeToString()
            # print(len(data))
            self.udpSender.send(data, ipForward_t+"."+format(info.ip), SEND_PORT)


#inforeceiver的拿到了一个paintinfo的回调函数 udprecv开了一个线程 一直执行receive 收到了就执行inforeceriver的本身的回调函数填数组 再执行paintinfo
class InfoViewer(QQuickPaintedItem):
    MAX_PLAYER = 16
    drawSignal = pyqtSignal(int,zss.Multicast_Status)
    statusSingnal=pyqtSignal(zss.Robot_Status)
    refresh=pyqtSignal(int)
    flag1=0
    flag2=0
    update_control=0
    only_one = True
    initFinish = False
    infoReceiverLock = threading.Lock()
    control_all = False
    control_all_which_team = False
    control_all_finish = False
    def __init__(self,parent=None):
        super().__init__(parent)
        # accept mouse event left click
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)
        self.receiverNeedStop = False
        self.infoReceiver = InfoReceiver(self.getNewInfo)
        self.cmdSender = CmdSender()

        self.udpRecv = network.QtMulticastReceiver(MC_ADDR, MC_PORT)
        self.udpRecv.dataReceived.connect(self.infoReceiver._cb)

        self.pointtopointRecv = network.QtPointToPointReceiver('0.0.0.0', SINGLE_PORT)
        self.pointtopointRecv.dataReceived.connect(self.parse_and_paint_signal)

        self.ifDraw = [False] * 32
        self.paintTimer = QTimer()
        self.paintTimer.timeout.connect(self.paintAllCheck)
        self.paintTimer.start(200)

        self.painter = QPainter()
        self.image = QImage(QSize(int(self.width()),int(self.height())),QImage.Format.Format_ARGB32_Premultiplied)
        self.ready = False
        self.drawSignal.connect(self.paintInfo)
        self.statusSingnal.connect(self.paint_single_info)
        self.refresh.connect(self.paintRefresh)
        self.initFinish = True
                
    def parse_and_paint_signal(self, data, ip_str):
        if self.ready and self.painter.isActive():
            robot_status = zss.Robot_Status()
            robot_status.ParseFromString(data)
            self.statusSingnal.emit(robot_status)

    def paintAllCheck(self):
        onlineTick_t = onlineTick
        now = int(datetime.now().timestamp() * 1000)  
        
        for i in range(32):
            infoDir = self.infoReceiver.info
            selectDir = self.infoReceiver.selected
            if now - onlineTick_t[i] < 2000:
                for info in list(infoDir.values()):
                    if (info.team-1)*16 + info.robot_id == i:
                        self.drawSignal.emit(i%16,info)
                        self.ifDraw[i] = True
            else:
                if self.ifDraw[i] == True:
                    self.refresh.emit(i)    
                    info_to_remove = None
                    for key,info in infoDir.items():
                        if info.robot_id+(info.team-1)*16 == i:
                            info_to_remove = key
                    
                    if info_to_remove != None:
                        infoDir.pop(info_to_remove)
                        self.infoReceiver.info = infoDir
                            
                    if i in selectDir.keys():
                        selectDir.pop(i)
                        
                    self.infoReceiver.selected = selectDir
                    self.ifDraw[i] = False 

                
    @pyqtSlot()
    def close(self):
        print("closing info viewer, stop recv thread")
        self.receiverNeedStop = True
        if needPlot:
            timer.stop()
            
    def getNewInfo(self,n,info):
        if self.initFinish:
        # print("got new info ",n,info)
            if self.ready and self.painter.isActive() and n >= 0 and n < self.MAX_PLAYER:
                # print("rev",info.robot_id,info.team)
                onlineLock.acquire()
                onlineTick[info.robot_id + (info.team-1)*16] = int(datetime.now().timestamp() * 1000)
                onlineLock.release()
            # print("online",onlineTick[info.robot_id + (info.team-1)*16],info.robot_id + (info.team-1)*16)
            # self.drawSignal.emit(n,info)    
            
    # 鼠标的功能：总的来说就是确定接收哪个机器人的信息
    # 具体实现就是在指定区域内点击鼠标后，确定一个index，然后找InfoReceiver里的内容，如果找到了，
    # 也就是现在可以和这个index作为id的机器人连接，然后点左键清空缓存，然后确定现在接收内容的机器人id，
    # 然后点其它键，就是手动断开和该index做id的机器人的连接并停止接收
    def mousePressEvent(self, event: QMouseEvent) -> None:
        index, team = self.getAreaIndex(event.pos())
        infoDir = self.infoReceiver.info
        selectDir = self.infoReceiver.selected
        for info in infoDir.values():
            
            if info.robot_id == index and info.team == team:
                if self.only_one:
                    if event.button() == Qt.MouseButton.LeftButton:
                        selectDir.clear()
                        selectDir[index+(info.team-1)*16] = info
                        self.infoReceiver.selected = selectDir
                        global ipForward
                        
                        self.pointtopointRecv.target_ip= ipForward + "."+format(info.ip)
                        self.pointtopointRecv.receive_flag = True
                        # print("else")
                        self.drawSignal.emit(index,info)
                        break
                    else :
                        if (index+(info.team-1)*16) in selectDir:
                            print(selectDir)
                            selectDir.pop(index+(info.team-1)*16)
                            self.infoReceiver.selected = selectDir
                            print(index+(info.team-1)*16)
                            self.pointtopointRecv.receive_flag = False
                            # print("else")
                            self.drawSignal.emit(index,info)
                            return
                else:
                    if event.button() == Qt.MouseButton.LeftButton:
                        selectDir[index+(info.team-1)*16] = info
                        self.infoReceiver.selected = selectDir
                        self.pointtopointRecv.target_ip= ipForward + "."+format(info.ip)
                        self.pointtopointRecv.receive_flag = True
                        # print("else")
                        self.drawSignal.emit(index,info)
                        break
                    else:
                        if (index+(info.team-1)*16) in selectDir:
                            selectDir.pop(index+(info.team-1)*16)
                            self.infoReceiver.selected = selectDir
                            self.pointtopointRecv.receive_flag = False
                            # print("else")
                            self.drawSignal.emit(index,info)
                            return
        

        
            
    @pyqtSlot(int, zss.Multicast_Status)
    def paintInfo(self, n, info):
        selectDir = self.infoReceiver.selected

        battery_v = info.battery / 10.0
        battery_ratio = max(0.0, min((battery_v - 15.0) / (16.8 - 15.0), 1.0))
        battery_percent = int(battery_ratio * 100)

        # 时尚电量颜色：HSL 模式，饱和度高、亮度高，色相从红(0°)渐变到绿(120°)
        hue = 120 * battery_ratio  # 0→红, 120→绿
        label_color = QColor.fromHsl(int(hue), 245, 230)  # 饱和度255，亮度220(约86%)
        fill_color = label_color  # 直接使用，不再额外提亮

        if info.team == 1:
            area_left = 0.0
            selected = n in selectDir
        else:
            area_left = 0.645
            selected = (n + 16) in selectDir

        # 阴影矩形（偏移量稍加大，颜色加深）
        shadow_rect = QRectF(self._x(n, area_left + 0.014), self._y(n, 0.12),
                            self._w(n, 0.29), self._h(n, 0.83))
        # 卡片矩形（去掉白色背景 panel_rect）
        card_rect = QRectF(self._x(n, area_left + 0.008), self._y(n, 0.06),
                        self._w(n, 0.29), self._h(n, 0.82))

        self.painter.setPen(Qt.PenStyle.NoPen)
        # 绘制阴影（增强：颜色更深）
        self.painter.setBrush(QColor(150, 150, 150, 100))
        self.painter.drawRoundedRect(shadow_rect, 7.5, 7.5)

        # 绘制彩色卡片
        self.painter.setBrush(fill_color)

        # 根据选中状态设置画笔：选中时用亮红色、宽度3；否则用深灰色、宽度1
        if selected:
            pen = QPen(QColor(255, 100, 100), 3)   # 亮红色，宽度3
        else:
            pen = QPen(QColor(45, 45, 45), 1)      # 深灰色，宽度1

        self.painter.setPen(pen)
        self.painter.drawRoundedRect(card_rect, 7.5, 7.5)

        # 绘制文字（无阴影）
        font = QFont('Arial', 10)
        self.painter.setFont(font)
        text = f"{info.ip}: {battery_percent}%,{info.infrared/10.0:.1f},{info.have_imu}"
        self.painter.setPen(QColor(15, 15, 15))
        self.painter.drawText(card_rect, Qt.AlignmentFlag.AlignCenter, text)

        self.update(self._area(n))
        
        
    @pyqtSlot(int)    
    def paintRefresh(self,n):
        if self.initFinish:
            id = n%16
            team = int(n/16)
            self.painter.setPen(QColor(50,50,50))
            self.painter.setBrush(QColor(50,50,50))
            self.painter.drawRect(QRectF(self._x(id,team*0.65), self._y(id,0.0), self._w(id,0.3),self._h(id,1.0)))
            self.update()
            self.update(self._area(n))

    def paint(self, painter):
        if self.ready:
            painter.drawImage(QRectF(0,0,self.width(),self.height()),self.image)
        pass
    
    @pyqtSlot(int,int)
    def resize(self, width, height):
        self.ready = False
        if width <= 0 or height <= 0:
            return
        if self.painter.isActive():
            self.painter.end()
        self.image = QImage(QSize(width, height), QImage.Format.Format_ARGB32_Premultiplied)
        self.painter.begin(self.image)
        self.ready = True

        for n in range(16):
            # 绘制整个槽位的灰色背景（保持不变）
            self.painter.setPen(QColor(50, 50, 50))
            self.painter.setBrush(QColor(50, 50, 50))
            self.painter.drawRect(QRectF(self._x(n, 0.0), self._y(n, 0.0),
                                        self._w(n, 1.0), self._h(n, 1.0)))
            self.update()

            # 绘制右侧数字区域：灰色背景，白色边框加粗，白色文字
            # 设置白色画笔，宽度1（加粗）
            self.painter.setPen(QPen(QColor(200, 200, 200), 1))
            # 设置灰色画刷（略亮于主背景，提高可读性）
            self.painter.setBrush(QColor(70, 70, 70))
            self.painter.drawRect(QRectF(self._x(n, 0.95), self._y(n, 0.0),
                                        self._w(n, 0.05), self._h(n, 1.0)))

            # 绘制白色数字
            self.painter.setFont(QFont('Helvetica', 11))
            self.painter.setPen(QColor(255, 255, 255))  # 白色文字
            self.painter.drawText(QRectF(self._x(n, 0.95), self._y(n, 0.0),
                                        self._w(n, 0.05), self._h(n, 1.0)),
                                Qt.AlignmentFlag.AlignCenter, format(n))
            self.update(self._area(n))
        
        
    def getAreaIndex(self,pos):
        yIndex = int(pos.y()/(self.height()/self.MAX_PLAYER))
        if pos.x() < 0.5 *self.width() :
            team = 1
        else:
            team = 2
        return yIndex,team
    def _area_blue(self,n):
        return QRect(int(self._x(n,0)), int(self._y(n,0)), int(self._w(n,0.3)),int(self._h(n,1)))
    def _area_yellow(self,n):
        return QRect(int(self._x(n,0.7)), int(self._y(n, 0)), int(self._w(n,0.3)), int(self._h(n, 1.0)))
    def _area(self,n):
        return QRect(int(self._x(n,0)), int(self._y(n, 0)), int(self._w(n,1.0)), int(self._h(n, 1.0)))
    def _x(self,n,v):
        return self.width()*(v)
    def _y(self,n,v):
        return self.height()/self.MAX_PLAYER*(n+v)
    def _w(self,n,v):
        return self.width()*(v)
    def _h(self,n,v):
        return self.height()/self.MAX_PLAYER*(v)
    @pyqtSlot(int,float,float,float,float,bool,bool,float,bool,float,bool,bool)
    def updateCommandParams(self,robotID,velX,velY,velR,ctrl,mode,shoot,power,use_imu,angle,control_all,control_all_which_team):
        self.cmdSender.updateCommandParams(robotID,velX,velY,velR,ctrl,mode,shoot,power,use_imu,angle)      
        self.control_all = control_all
        self.control_all_which_team = control_all_which_team
        
        if (self.control_all == False and self.control_all_finish == True):
            self.control_all_finish = False
            self.infoReceiver.selected.clear()
        
        if (self.control_all_finish != True and self.control_all == True):
            self.control_all_team()
             
    def control_all_team(self):
        self.pointtopointRecv.receive_flag = False
        self.infoReceiver.selected.clear()
        if (self.control_all_which_team == False):
            for info in self.infoReceiver.info.values():
                index = info.robot_id+(info.team-1)*16
                if index < 16:
                    self.infoReceiver.selected[index] = info
                    self.drawSignal.emit(index,info)
        else:
            for info in self.infoReceiver.info.values():
                index = info.robot_id+(info.team-1)*16
                if index >= 16:
                    self.infoReceiver.selected[index] = info
                    self.drawSignal.emit(index,info)
        self.control_all_finish = True
    
    @pyqtSlot()
    def sendCommand(self):
        
        global needPlot
        global plotInitFinish
        
        if needPlot and plotInitFinish:
        
            global length
            global plotData
            global plotDataList
            global plotDataNum
            
            for index in range(plotDataNum):
                plotDataList[index].append(plotData[index])
            
            if slide == True:
                length += 1    
                       
        global changeSendTick
        if changeSendTick == 5 and self.cmdSender.pb_data.need_change_team == False and self.cmdSender.pb_data.need_change_id == False:
            self.infoReceiver.selected.clear()
            changeSendTick = 0
        
        self.cmdSender.sendCommand(self.infoReceiver)
        
        

    def paint_signal(self,info):
        if self.ready and self.painter.isActive():
            self.statusSingnal.emit(info)

    @pyqtSlot(zss.Robot_Status)
    def paint_single_info(self,info):
        if self.initFinish:
            # Base panel background by team color.
            if info.team == 1:
                team = "蓝"
                panel_bg = QColor.fromHsl(240, 255, 150)
                row_bg = QColor.fromHsl(240, 255, 235)
            else:
                team = "黄"
                panel_bg = QColor.fromHsl(60, 255, 150)
                row_bg = QColor.fromHsl(60, 255, 235)

            self.painter.setPen(Qt.PenStyle.NoPen)
            self.painter.setBrush(panel_bg)
            for i in range(16):
                self.painter.drawRect(QRectF(self._x(i,0.302), self._y(i,0.0), self._w(i,0.346),self._h(i,1.0)))

            # Use bold SimHei to keep style consistent with broadcast cards.
            status_font = QFont('SimHei', 13)
            # status_font.setBold(True)
            self.painter.setFont(status_font)

            if self.pointtopointRecv.receive_flag:

                battery_v = info.battery / 10.0
                battery_str = "{:.1f}".format(battery_v)
                capacitance_str = "{:.1f}".format(info.capacitance/10.0)
                if info.team ==1:
                    team="蓝"
                else :
                    team="黄"
                angle_z_str="{:.3f}".format(info.imu_data[10])
                angle_y_str = "{:.3f}".format(info.imu_data[9])
                angle_x_str = "{:.3f}".format(info.imu_data[8])
                w_x_str="{:.3f}".format(info.imu_data[4])
                w_y_str = "{:.3f}".format(info.imu_data[5])
                w_z_str = "{:.3f}".format(info.imu_data[6])
                wheel0_str="{:.0f}".format(info.wheel_encoder[0])
                wheel1_str = "{:.0f}".format(info.wheel_encoder[1])
                wheel2_str = "{:.0f}".format(info.wheel_encoder[2])
                wheel3_str = "{:.0f}".format(info.wheel_encoder[3])
                infrared_str = "{:.0f}".format(info.infrared)
                # Draw one rounded label row with subtle shadow and optional highlight color.
                def draw_info_row(idx, content, text_color=QColor(25, 25, 25), bg_color=row_bg):
                    card_rect = QRectF(
                        self._x(idx, 0.305),
                        self._y(idx, 0.04),
                        self._w(idx, 0.34),
                        self._h(idx, 0.9),
                    )

                    # Add edge stroke for better contrast between rows.
                    self.painter.setPen(QColor(110, 120, 130, 150))
                    self.painter.setBrush(bg_color)
                    self.painter.drawRoundedRect(card_rect, 8.0, 8.0)

                    text_rect_shadow = QRectF(
                        card_rect.x() + 1.2,
                        card_rect.y() + 1.2,
                        card_rect.width(),
                        card_rect.height(),
                    )
                    self.painter.setPen(QColor(0, 0, 0, 70))
                    # self.painter.drawText(
                    #     text_rect_shadow,
                    #     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    #     "  " + content,
                    # )

                    self.painter.setPen(text_color)
                    self.painter.drawText(
                        card_rect,
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        "  " + content,
                    )

                rows = [
                    (0, "车号: " + str(info.robot_id), QColor(10, 10, 10), row_bg),
                    (1, "车队: " + str(team), QColor(10, 10, 10), row_bg),
                    (2, "0 号轮速度: " + str(wheel0_str), QColor(10, 10, 10), row_bg),
                    (3, "1 号轮速度: " + str(wheel1_str), QColor(10, 10, 10), row_bg),
                    (4, "2 号轮速度: " + str(wheel2_str), QColor(10, 10, 10), row_bg),
                    (5, "3 号轮速度: " + str(wheel3_str), QColor(10, 10, 10), row_bg),
                    (6, "电容电压/V " + capacitance_str, QColor(10, 10, 10), row_bg),
                    (7, "电池电量/V " + battery_str, QColor(10, 10, 10), row_bg),
                    (8, "红外时间 " + str(infrared_str), QColor(10, 10, 10), row_bg),
                    (9, "X 轴角度 " + str(angle_x_str), QColor(10, 10, 10), row_bg),
                    (10, "Y 轴角度 " + str(angle_y_str), QColor(10, 10, 10), row_bg),
                    (11, "Z 轴角度 " + str(angle_z_str), QColor(10, 10, 10), row_bg),
                    (12, "X 轴角速度 " + w_x_str, QColor(10, 10, 10), row_bg),
                    (13, "Y 轴角速度 " + w_y_str, QColor(10, 10, 10), row_bg),
                    (14, "Z 轴加速度 " + w_z_str, QColor(10, 10, 10), row_bg),
                ]

                for idx, content, text_color, bg_color in rows:
                    draw_info_row(idx, content, text_color, bg_color)
                
                global ipForward

                draw_info_row(15, "ip: " + ipForward, QColor(10, 10, 10), row_bg)
                
                global plotData
                global plotInitFinish
                global needPlot
                        
                if needPlot and plotInitFinish: 
                    for i in range(len(fdbNeedPlotName)):
                        plotData[i] = eval(fdbNeedPlotName[i])
                            
            self.update()
        
    @pyqtSlot(bool)    
    def car_num(self,only_one):
        self.only_one = only_one

    @pyqtSlot(int)
    def changeTeam(self, team_new):
        if team_new not in (zss.Team.BLUE, zss.Team.YELLOW):
            return

        self.pointtopointRecv.receive_flag = False
        self.infoReceiver.selected.clear()
        for info in self.infoReceiver.info.values():
            self.infoReceiver.selected[info.robot_id + (info.team - 1) * 16] = info

        self.cmdSender.changeTeam(team_new)

    @pyqtSlot(int)
    def changeId(self, id_new):
        if id_new < 0 or id_new > 15:
            return

        self.pointtopointRecv.receive_flag = False
        self.infoReceiver.selected.clear()
        for info in self.infoReceiver.info.values():
            self.infoReceiver.selected[info.robot_id + (info.team - 1) * 16] = info

        self.cmdSender.changeId(id_new)
         
        
    @pyqtSlot()    
    def plotStart(self):
        # if plotGoal != whichPlotEnum.kNone:
        #     timer.start(10)#多少ms调用一次
        if needPlot:
            timer.start(8)
      
    @pyqtSlot()  
    def plotStop(self):
        # if plotGoal != whichPlotEnum.kNone:
        #     timer.stop()
        if needPlot:
            timer.stop()
    



top = 0.5
bottom = -0.5
slide = False

def plotCallback():
    
    global length
    global top
    global bottom
    global slide
    global plotData
    global plotDataList
    global historyLength
    global plotDataNum
            
    
    lenMoreThanOne = True
    
    for index in range(plotDataNum):
        lenMoreThanOne =  lenMoreThanOne and (len(plotDataList[index]) > 1)
        
    if lenMoreThanOne:
        for index in range(plotDataNum):
            if plotDataList[index][-1] > top:
                top = plotDataList[index][-1]
            elif plotDataList[index][-1] < bottom:
                bottom = plotDataList[index][-1]
                
    noSlide = True
    
    for index in range(plotDataNum):
        noSlide = noSlide and (len(plotDataList[index])<historyLength)
        
    if noSlide:
        p.setRange(xRange=[0, historyLength+0], yRange=[bottom, top], update=False)
    else:
        p.setRange(xRange=[length, historyLength+length], yRange=[bottom, top], update=False)
        slide = True    
    
    for index in range(plotDataNum):
        curve[index].setData(plotDataList[index])
    
isFdb = True

def is_nested_field_exists(field_path: list[str], message_class) -> bool:
    descriptor = message_class.DESCRIPTOR
    for field_name in field_path:
        if field_name not in descriptor.fields_by_name:
            return False
        field = descriptor.fields_by_name[field_name]
        descriptor = field.message_type  # 进入下一层描述符
    return True

if __name__ == '__main__':
    # AppImage environments may not provide usable GLX/EGL; force software rendering.
    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
    os.environ.setdefault("QT_OPENGL", "software")
    os.environ.setdefault("QT_XCB_GL_INTEGRATION", "none")
    os.environ.setdefault("QSG_RHI_BACKEND", "software")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Fusion"
    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()
    qmlRegisterType(InfoViewer, 'ZSS', 1, 0, 'InfoViewer')
    
    needPlotTmp = True
        
    with open(resource_path('zcrazy.txt'),'r') as file:
        for line in file:
            if needPlotTmp and line.strip() != 'true:':
                needPlotTmp = False  
                needPlot = False    
                break             
            else:
                needPlotTmp = False
                needPlot = True
                if line.strip()[0] == "-":
                    isFdb = False
                else:
                    if isFdb:
                        tmp = line.strip().split()
                        tmpNum = ""
                        tmpPath = tmp[0].split(".")
                        if is_nested_field_exists(tmpPath,zss.Robot_Status):
                            for i in tmp:
                                tmpNum = tmpNum+i
                            fdbNeedPlotName.append(fdbPlotForward+tmpNum)
                    else:
                        tmp = line.strip().split()
                        tmpNum = ""
                        tmpPath = tmp[0].split(".")
                        if is_nested_field_exists(tmpPath,zss.Robot_Command):
                            for i in tmp:
                                tmpNum = tmpNum+i
                            refNeedPlotName.append(refPlotForward+tmpNum)
                
                
    print(needPlot)
      
    plotDataNum = len(fdbNeedPlotName) + len(refNeedPlotName)  
    
    print(plotDataNum)
    print(fdbNeedPlotName)
    print(refNeedPlotName)
    
    global plotData
    global plotDataList
    global plotInitFinish
    
    plotData = [0]*plotDataNum
    plotDataList = [[] for _ in range(plotDataNum)]
    plotInitFinish = True
                                
    if needPlot and plotInitFinish:
        
        curve = []
        
        win = pg.GraphicsLayoutWidget(show=True)#建立窗口
        win.setWindowTitle(u'zcrazy')
        win.resize(800, 500)#小窗口大小

        historyLength = 100#横坐标长度
        p = win.addPlot()#把图p加入到窗口中
        p.showGrid(x=True, y=True)#把X和Y的表格打开    
        
           
        for index in range(plotDataNum):
            curve.append(p.plot())
        
        
        length=0
        timer = pg.QtCore.QTimer()
        timer.timeout.connect(plotCallback)#定时调用plotCallback函数
    
    
    # 创建 InfoViewer 实例
    # 连接退出信号
    engine.quit.connect(app.quit)
    # 加载QML文件
    try:
        engine.load(resource_path('main.qml'))
    except Exception as e:
        print("Failed to load QML:", e)
        sys.exit(1)
    # 执行应用程序
    res = app.exec()
    # 清理资源
    del engine
    sys.exit(res)
    # udpSender = UdpSender()
    # while True:
    #     time.sleep(1)


