import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 2.15
import RinUI

FluentPage {
    title: qsTr("总览")

    property string apiBase: "http://127.0.0.1:24300"
    property int accountsTotal: 0
    property int cachedLogins: 0
    property int requests24h: 0
    property int activeTokens: 0
    property int requests5m: 0
    property string updatedAt: ""

    function loadMetrics() {
        var xhr = new XMLHttpRequest()
        xhr.open("GET", apiBase + "/metrics")
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                var obj = JSON.parse(xhr.responseText)
                var d = obj.data || {}
                accountsTotal = d.accounts_total || 0
                cachedLogins = d.cached_logins || 0
                requests24h = d.requests_24h || 0
                activeTokens = d.active_tokens || 0
                requests5m = d.requests_5m || 0
                updatedAt = d.updated_at || ""
                activityModel.clear()
                var logs = d.logs || []
                for (var i = 0; i < logs.length; i++) {
                    activityModel.append({ title: logs[i].text || "", time: logs[i].time || "" })
                }
            }
        }
        xhr.send()
    }

    Component.onCompleted: loadMetrics()
    Timer { interval: 5000; running: true; repeat: true; onTriggered: loadMetrics() }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Frame {
                Layout.fillWidth: true
                Layout.preferredWidth: 300
                Layout.preferredHeight: 120
                Column {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 6
                    Text { text: qsTr("已登录账号") ; font.pointSize: 14 }
                    Text { text: accountsTotal ; font.pointSize: 28 }
                }
            }
            Frame {
                Layout.fillWidth: true
                Layout.preferredWidth: 300
                Layout.preferredHeight: 120
                Column {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 6
                    Text { text: qsTr("缓存登录") ; font.pointSize: 14 }
                    Text { text: cachedLogins ; font.pointSize: 28 }
                }
            }
            Frame {
                Layout.fillWidth: true
                Layout.preferredWidth: 300
                Layout.preferredHeight: 120
                Column {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 6
                    Text { text: qsTr("24h 请求") ; font.pointSize: 14 }
                    Text { text: requests24h ; font.pointSize: 28 }
                }
            }
        }

        Frame {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Column {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8
                Text { text: qsTr("最近活动") ; font.pointSize: 16 }
                ListModel { id: activityModel }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: activityModel
                    delegate: RowLayout {
                        width: parent.width
                        spacing: 12
                        Label { Layout.fillWidth: true; text: title }
                        Label { text: time }
                    }
                }
            }
        }
    }
}
