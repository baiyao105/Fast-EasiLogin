import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 2.15
import RinUI

FluentPage {
    title: qsTr("关于")

    Column {
        Layout.fillWidth: true
        spacing: 12

        Text {
            text: qsTr("Seewo Fast-Login 控制台")
            font.pointSize: 16
        }

        Text {
            text: qsTr("版本 0.1.0 © 2025")
            color: "#666"
        }
    }
}
