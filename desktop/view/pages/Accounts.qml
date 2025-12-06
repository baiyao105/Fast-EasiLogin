import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 2.15
import RinUI

FluentPage {
    title: qsTr("账户管理")

    Column {
        Layout.fillWidth: true
        spacing: 12

        Text {
            text: qsTr("管理本地账户数据")
            font.pointSize: 16
        }

        Text {
            text: qsTr("后续可在此展示和编辑用户列表")
            color: "#666"
        }
    }
}

