import QtQuick
import QtQuick.Controls
import ZSS as ZSS
ApplicationWindow {
    visible: true
    width: 1280
    height: 600
    title: "Zrazy"
    property bool needChangeTeamTickEnable: false
    Timer{
        id:timer;
        interval:8;
        running:false;
        repeat:true;
        onTriggered: {
            
            // if(switchControl.checked)
            //     crazyShow.updateFromGamepad();
            // ui.cmdUI.updateCommand();//调用serial.updateCommandParams()
            infoViewer.sendCommand();//把数据发出去
        }
    }

    Timer {
        id: resetTimer
        interval: 1000  // 1秒自动恢复
        repeat: false
        onTriggered: needChangeTeamTickEnable = false
    }

    onClosing: {
        infoViewer.close();
    }
    Rectangle{
        width:parent.width-infoViewerRect.width
        height:parent.height
        anchors.left:parent.left
        color:"#222"

        focus: true
        Keys.onPressed: (event) => {
            if (event.key === Qt.Key_T) {  // 示例使用空格键
                needChangeTeamTickEnable = true
                resetTimer.restart()
                event.accepted = true
            }
        }
        UI{
            needChangeTeamState : needChangeTeamTickEnable
            cmdSender:infoViewer
        }
    }
    Rectangle{
        id:infoViewerRect
        width:500
        height:parent.height
        anchors.right:parent.right
        color:"#444"
        ZSS.InfoViewer{
            id: infoViewer
            anchors.fill:parent
            onWidthChanged: this.resize(width,height)
            onHeightChanged: this.resize(width,height)
            needChangeTeam:needChangeTeamTickEnable
        }
    }

}