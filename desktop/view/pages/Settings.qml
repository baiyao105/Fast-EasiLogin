import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 2.15
import RinUI

FluentPage {
    title: qsTr("设置")

    Column {
        Layout.fillWidth: true
        spacing: 12

        Text {
            text: qsTr("应用设置")
            font.pointSize: 16
        }

        Text {
            text: qsTr("在此调整偏好与行为")
            color: "#666"
        }
    }
}

