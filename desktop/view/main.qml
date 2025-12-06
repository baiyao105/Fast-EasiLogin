import QtQuick 2.15
import QtQuick.Controls 2.15
import RinUI

FluentWindow {
    id: window
    visible: true
    width: 1100
    height: 700
    minimumWidth: 600
    minimumHeight: 400

    navigationItems: [
        {
            title: qsTr("总览"),
            page: Qt.resolvedUrl("pages/Dashboard.qml"),
            icon: "ic_fluent_home_20_regular"
        },
        {
            title: qsTr("账户管理"),
            page: Qt.resolvedUrl("pages/Accounts.qml"),
            icon: "ic_fluent_people_20_regular"
        },
        {
            title: qsTr("设置"),
            page: Qt.resolvedUrl("pages/Settings.qml"),
            icon: "ic_fluent_settings_20_regular"
        },
        {
            title: qsTr("关于"),
            page: Qt.resolvedUrl("pages/About.qml"),
            icon: "ic_fluent_info_20_regular"
        }
    ]
}

