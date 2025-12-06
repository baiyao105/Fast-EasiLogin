import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 2.15
import RinUI

FluentPage {
    title: qsTr("总览")

    Column {
        Layout.fillWidth: true
        spacing: 12

        Text {
            text: qsTr("系统总览")
            font.pointSize: 18
        }

        Text {
            text: qsTr("这里展示应用的概览信息与状态")
            color: "#666"
        }
    }
}

