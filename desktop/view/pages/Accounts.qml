import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 2.15
import RinUI

FluentPage {
    title: qsTr("班级管理")

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            TextField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: qsTr("搜索学生/学号")
            }
            ComboBox {
                id: statusFilter
                model: [qsTr("全部"), qsTr("在读"), qsTr("休学")]
                currentIndex: 0
            }
            Button { text: qsTr("新增学生") }
            Button { text: qsTr("导入") }
            Button { text: qsTr("导出") }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Item {
                implicitWidth: 260
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8

                    Text { text: qsTr("班级列表"); font.pointSize: 16 }
                    ListModel {
                        id: classModel
                        ListElement { name: "一年一班"; count: 32 }
                        ListElement { name: "一年二班"; count: 30 }
                        ListElement { name: "二年一班"; count: 35 }
                    }
                    ListView {
                        id: classList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: classModel
                        delegate: ItemDelegate {
                            width: classList.width
                            text: name + " (" + count + ")"
                            onClicked: classList.currentIndex = index
                        }
                        currentIndex: 0
                    }
                    Button { text: qsTr("新增班级") }
                }
            }

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8

                    Text { text: qsTr("学生列表"); font.pointSize: 16 }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Label { text: qsTr("当前班级:") }
                        Label { text: classModel.get(classList.currentIndex).name }
                        Item { Layout.fillWidth: true }
                        Button { text: qsTr("批量删除") }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: "#e5e5e5" }

                    ListModel {
                        id: studentModel
                        ListElement { name: "张三"; sid: "20250001"; gender: "男"; clazz: "一年一班"; status: "在读" }
                        ListElement { name: "李四"; sid: "20250002"; gender: "女"; clazz: "一年一班"; status: "在读" }
                        ListElement { name: "王五"; sid: "20250003"; gender: "男"; clazz: "一年一班"; status: "休学" }
                        ListElement { name: "赵六"; sid: "20250004"; gender: "女"; clazz: "一年一班"; status: "在读" }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Label { Layout.preferredWidth: 160; text: qsTr("姓名") }
                            Label { Layout.preferredWidth: 160; text: qsTr("学号") }
                            Label { Layout.preferredWidth: 80; text: qsTr("性别") }
                            Label { Layout.preferredWidth: 160; text: qsTr("班级") }
                            Label { Layout.preferredWidth: 100; text: qsTr("状态") }
                            Item { Layout.fillWidth: true }
                        }
                        Rectangle { Layout.fillWidth: true; height: 1; color: "#e5e5e5" }

                        ListView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            model: studentModel
                            clip: true
                            delegate: RowLayout {
                                width: parent.width
                                spacing: 12
                                Label { Layout.preferredWidth: 160; text: name }
                                Label { Layout.preferredWidth: 160; text: sid }
                                Label { Layout.preferredWidth: 80; text: gender }
                                Label { Layout.preferredWidth: 160; text: clazz }
                                Label { Layout.preferredWidth: 100; text: status }
                                Item { Layout.fillWidth: true }
                                Button { text: qsTr("编辑") }
                                Button { text: qsTr("删除") }
                            }
                        }
                    }
                }
            }
        }
    }
}
