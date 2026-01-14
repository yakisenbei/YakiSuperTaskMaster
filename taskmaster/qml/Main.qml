import QtQuick 6.10
import QtQuick.Controls 6.10
import QtQuick.Layouts 6.10

ApplicationWindow {
    id: win
    width: 1200
    height: 720
    visible: true
    title: "TaskMaster"

    property var controller: TM

    property string selectedTaskId: ""
    property int selectedRow: -1

    Connections {
        target: controller
        function onViewChanged() {
            win.selectedTaskId = ""
            win.selectedRow = -1
        }
    }

    function currentModel() {
        if (controller.currentView === "due") return controller.dueModel
        if (controller.currentView === "waiting") return controller.waitingModel
        if (controller.currentView === "archived") return controller.archivedModel
        return null
    }

    function selectByTaskId(taskId) {
        const m = currentModel()
        if (!m || !taskId) return
        const row = m.findRowByTaskId(taskId)
        if (row >= 0) {
            win.selectedRow = row
            win.selectedTaskId = m.taskIdAtRow(row)
            if (tableView && tableView.positionViewAtRow) {
                tableView.positionViewAtRow(row, TableView.Contain)
            }
        } else {
            win.selectedRow = m.rowCount() > 0 ? 0 : -1
            win.selectedTaskId = win.selectedRow >= 0 ? m.taskIdAtRow(win.selectedRow) : ""
            if (tableView && tableView.positionViewAtRow && win.selectedRow >= 0) {
                tableView.positionViewAtRow(win.selectedRow, TableView.Contain)
            }
        }
    }

    background: Item {
        anchors.fill: parent

        Rectangle {
            anchors.fill: parent
            color: "#1E1E1E"
        }

        Image {
            anchors.fill: parent
            source: controller.backgroundPath
            fillMode: Image.PreserveAspectCrop
            visible: source !== ""
            smooth: true
            mipmap: true
        }
    }

    // Menus are currently disabled because QtQuick.Controls Menu/MenuBar are broken in this Qt/PySide build.
    // All actions are accessible via keyboard shortcuts and the row context menu will be replaced with a custom (non-Menu) popup.

    // Global shortcuts (spec defaults)
    Shortcut { sequence: "Ctrl+N"; onActivated: newTaskDialog.open() }
    Shortcut { enabled: !commandPalette.visible; sequence: "F2"; onActivated: detailsDialog.openWithSelected(true) }
    Shortcut { enabled: !commandPalette.visible; sequence: "Ctrl+S"; onActivated: if (controller.currentView === "due" && win.selectedTaskId !== "") controller.completeTask(win.selectedTaskId, "good") }
    Shortcut { enabled: !commandPalette.visible; sequence: "1"; onActivated: if (controller.currentView === "due" && win.selectedTaskId !== "") controller.completeTask(win.selectedTaskId, "again") }
    Shortcut { enabled: !commandPalette.visible; sequence: "2"; onActivated: if (controller.currentView === "due" && win.selectedTaskId !== "") controller.completeTask(win.selectedTaskId, "hard") }
    Shortcut { enabled: !commandPalette.visible; sequence: "3"; onActivated: if (controller.currentView === "due" && win.selectedTaskId !== "") controller.completeTask(win.selectedTaskId, "good") }
    Shortcut { enabled: !commandPalette.visible; sequence: "4"; onActivated: if (controller.currentView === "due" && win.selectedTaskId !== "") controller.completeTask(win.selectedTaskId, "easy") }
    Shortcut { enabled: !commandPalette.visible; sequence: "Delete"; onActivated: if ((controller.currentView === "due" || controller.currentView === "waiting") && win.selectedTaskId !== "") controller.archiveTask(win.selectedTaskId) }
    Shortcut { enabled: !commandPalette.visible; sequence: "Ctrl+R"; onActivated: if (controller.currentView === "archived" && win.selectedTaskId !== "") controller.restoreTask(win.selectedTaskId) }
    Shortcut { enabled: !commandPalette.visible; sequence: "Shift+Delete"; onActivated: if (controller.currentView === "archived" && win.selectedTaskId !== "") purgeConfirmDialog.openFor(win.selectedTaskId) }
    Shortcut { sequence: "Ctrl+1"; onActivated: controller.setView("due") }
    Shortcut { sequence: "Ctrl+2"; onActivated: controller.setView("waiting") }
    Shortcut { sequence: "Ctrl+3"; onActivated: controller.setView("archived") }
    Shortcut { sequence: "Ctrl+4"; onActivated: controller.setView("settings") }
    Shortcut { sequence: "Ctrl+F"; onActivated: searchField.forceActiveFocus() }
    Shortcut { sequence: "F5"; onActivated: controller.refresh() }
    Shortcut { sequence: "Ctrl+Shift+R"; onActivated: recalcConfirmDialog.open() }
        Shortcut { sequence: "Ctrl+P"; onActivated: commandPalette.openGlobal() }
        Shortcut { sequence: "Shift+F10"; onActivated: commandPalette.openContextFromSelection() }

        function _handleEscape() {
            // Close topmost transient UI first.
            if (commandPalette.visible) {
                commandPalette.close()
                return
            }
            if (detailsDialog.visible) {
                if (detailsDialog.editMode) {
                    detailsDialog.editMode = false
                    detailsDialog.reload()
                } else {
                    detailsDialog.close()
                }
                return
            }
            if (newTaskDialog.visible) {
                newTaskDialog.close()
                newTitle.text = ""
                newNote.text = ""
                return
            }
            if (purgeConfirmDialog.visible) {
                purgeConfirmDialog.close()
                return
            }
            if (recalcConfirmDialog.visible) {
                recalcConfirmDialog.close()
                return
            }

            // Non-modal fallbacks.
            if (controller.currentView === "settings") {
                controller.setView("due")
                tableView.forceActiveFocus()
                return
            }

            // Search behavior (keep it convenient).
            if (searchField.text && searchField.text.length > 0) {
                searchField.text = ""
                controller.setSearchQuery("")
                tableView.forceActiveFocus()
                return
            }

            tableView.forceActiveFocus()
        }

        // Global cancel/back (works regardless of focus)
        Shortcut { sequences: [ StandardKey.Cancel ]; context: Qt.ApplicationShortcut; onActivated: win._handleEscape() }

        function _hasSelection() {
                return win.selectedTaskId !== "" && win.selectedRow >= 0
        }

        function _currentTitleForSelection() {
            if (!tableView.model || win.selectedRow < 0) return ""
            return tableView.model.cellDisplay(win.selectedRow, 0)
        }

        Popup {
                id: commandPalette
                modal: true
                focus: true
                padding: 0
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                property string mode: "global" // global|context
                property bool _opening: false

                width: mode === "global" ? 760 : 420
                height: mode === "global" ? 460 : 360

                background: Rectangle {
                        radius: 12
                        color: Qt.rgba(0x2D/255,0x2D/255,0x30/255, 0.95)
                        border.color: "#3C3C3C"
                }

                Overlay.modal: Rectangle { color: Qt.rgba(0, 0, 0, 0.35) }

                ListModel { id: paletteModel }

                function _makeCommands() {
                        const hasSel = win._hasSelection()
                        const inDue = controller.currentView === "due"
                        const inWaiting = controller.currentView === "waiting"
                        const inArchived = controller.currentView === "archived"

                        return [
                                { group: "Task", title: "New Task…", shortcut: "Ctrl+N", contextOnly: false,
                                    enabled: true, run: () => newTaskDialog.open() },

                                { group: "Task", title: "Open Details", shortcut: "Enter", contextOnly: false,
                                    enabled: hasSel && controller.currentView !== "settings", run: () => detailsDialog.openWithSelected(false) },
                                { group: "Task", title: "Edit…", shortcut: "F2", contextOnly: true,
                                    enabled: hasSel && controller.currentView !== "settings", run: () => detailsDialog.openWithSelected(true) },

                                { group: "Review", title: "Complete: Again", shortcut: "1", contextOnly: true,
                                    enabled: hasSel && inDue, run: () => controller.completeTask(win.selectedTaskId, "again") },
                                { group: "Review", title: "Complete: Hard", shortcut: "2", contextOnly: true,
                                    enabled: hasSel && inDue, run: () => controller.completeTask(win.selectedTaskId, "hard") },
                                { group: "Review", title: "Complete: Good", shortcut: "3 / Ctrl+S", contextOnly: true,
                                    enabled: hasSel && inDue, run: () => controller.completeTask(win.selectedTaskId, "good") },
                                { group: "Review", title: "Complete: Easy", shortcut: "4", contextOnly: true,
                                    enabled: hasSel && inDue, run: () => controller.completeTask(win.selectedTaskId, "easy") },

                                { group: "Task", title: "Archive", shortcut: "Del", contextOnly: true,
                                    enabled: hasSel && (inDue || inWaiting), run: () => controller.archiveTask(win.selectedTaskId) },
                                { group: "Task", title: "Restore", shortcut: "Ctrl+R", contextOnly: true,
                                    enabled: hasSel && inArchived, run: () => controller.restoreTask(win.selectedTaskId) },
                                { group: "Task", title: "Purge…", shortcut: "Shift+Del", contextOnly: true,
                                    enabled: hasSel && inArchived, run: () => purgeConfirmDialog.openFor(win.selectedTaskId) },

                                { group: "Clipboard", title: "Copy Title", shortcut: "", contextOnly: true,
                                    enabled: hasSel && controller.currentView !== "settings", run: () => controller.copyText(win._currentTitleForSelection()) },

                                { group: "View", title: "Go to Due", shortcut: "Ctrl+1", contextOnly: false,
                                    enabled: true, run: () => controller.setView("due") },
                                { group: "View", title: "Go to Waiting", shortcut: "Ctrl+2", contextOnly: false,
                                    enabled: true, run: () => controller.setView("waiting") },
                                { group: "View", title: "Go to Archived", shortcut: "Ctrl+3", contextOnly: false,
                                    enabled: true, run: () => controller.setView("archived") },
                                { group: "View", title: "Go to Settings", shortcut: "Ctrl+4", contextOnly: false,
                                    enabled: true, run: () => controller.setView("settings") },

                                { group: "App", title: "Refresh", shortcut: "F5", contextOnly: false,
                                    enabled: true, run: () => controller.refresh() },
                                { group: "App", title: "Recalculate All Tasks…", shortcut: "Ctrl+Shift+R", contextOnly: false,
                                    enabled: true, run: () => recalcConfirmDialog.open() },

                                { group: "Theme", title: "Theme: Dark", shortcut: "", contextOnly: false,
                                    enabled: true, run: () => controller.setTheme("dark") },
                                { group: "Theme", title: "Theme: Light", shortcut: "", contextOnly: false,
                                    enabled: true, run: () => controller.setTheme("light") }
                        ]
                }

                function rebuild() {
                        const filter = paletteFilter.text.trim().toLowerCase()
                        const showContextOnly = (mode === "context")

                        paletteModel.clear()
                        const commands = _makeCommands()
                        for (let i = 0; i < commands.length; i++) {
                                const c = commands[i]
                                if (showContextOnly && !c.contextOnly) continue

                                const hay = (c.group + " " + c.title + " " + c.shortcut).toLowerCase()
                                if (filter && hay.indexOf(filter) === -1) continue

                                paletteModel.append({
                                        group: c.group,
                                        title: c.title,
                                        shortcut: c.shortcut,
                                        enabled: !!c.enabled,
                                        _idx: i
                                })
                        }
                        listView.currentIndex = paletteModel.count > 0 ? 0 : -1
                }

                function _runCurrent() {
                        if (listView.currentIndex < 0) return
                        const row = paletteModel.get(listView.currentIndex)
                        if (!row.enabled) return

                        const commands = _makeCommands()
                        const cmd = commands[row._idx]
                        close()
                        cmd.run()
                }

                function openGlobal() {
                        mode = "global"
                        x = (win.width - width) / 2
                        y = Math.max(24, (win.height - height) / 5)
                        paletteFilter.text = ""
                        open()
                }

                function openContextAt(item, localX, localY) {
                        mode = "context"
                        const p = item.mapToItem(win.contentItem, localX, localY)
                        x = Math.max(12, Math.min(p.x, win.width - width - 12))
                        y = Math.max(12, Math.min(p.y, win.height - height - 12))
                        paletteFilter.text = ""
                        open()
                }

                function openContextFromSelection() {
                        if (!win._hasSelection()) {
                                openGlobal()
                                return
                        }
                        mode = "context"
                        x = (win.width - width) / 2
                        y = Math.max(24, (win.height - height) / 5)
                        paletteFilter.text = ""
                        open()
                }

                onOpened: {
                        rebuild()
                    if (mode === "context") {
                        listView.forceActiveFocus()
                    } else {
                        paletteFilter.forceActiveFocus()
                    }
                }

                // Popup-scoped shortcuts so actions work even when focus is in a TextField.
                Shortcut {
                    enabled: commandPalette.visible
                    sequence: "Return"
                    onActivated: commandPalette._runCurrent()
                }
                Shortcut {
                    enabled: commandPalette.visible
                    sequence: "Enter"
                    onActivated: commandPalette._runCurrent()
                }
                Shortcut {
                    enabled: commandPalette.visible
                    sequence: "F2"
                    onActivated: {
                        if (win._hasSelection() && controller.currentView !== "settings") {
                            commandPalette.close()
                            detailsDialog.openWithSelected(true)
                        }
                    }
                }
                Shortcut {
                    enabled: commandPalette.visible && !paletteFilter.activeFocus
                    sequence: "Delete"
                    onActivated: {
                        if (win._hasSelection() && (controller.currentView === "due" || controller.currentView === "waiting")) {
                            commandPalette.close()
                            controller.archiveTask(win.selectedTaskId)
                        }
                    }
                }
                Shortcut {
                    enabled: commandPalette.visible
                    sequence: "Ctrl+R"
                    onActivated: {
                        if (win._hasSelection() && controller.currentView === "archived") {
                            commandPalette.close()
                            controller.restoreTask(win.selectedTaskId)
                        }
                    }
                }
                Shortcut {
                    enabled: commandPalette.visible
                    sequence: "Shift+Delete"
                    onActivated: {
                        if (win._hasSelection() && controller.currentView === "archived") {
                            commandPalette.close()
                            purgeConfirmDialog.openFor(win.selectedTaskId)
                        }
                    }
                }
                Shortcut {
                    enabled: commandPalette.visible && !paletteFilter.activeFocus
                    sequence: "1"
                    onActivated: {
                        if (win._hasSelection() && controller.currentView === "due") {
                            commandPalette.close()
                            controller.completeTask(win.selectedTaskId, "again")
                        }
                    }
                }
                Shortcut {
                    enabled: commandPalette.visible && !paletteFilter.activeFocus
                    sequence: "2"
                    onActivated: {
                        if (win._hasSelection() && controller.currentView === "due") {
                            commandPalette.close()
                            controller.completeTask(win.selectedTaskId, "hard")
                        }
                    }
                }
                Shortcut {
                    enabled: commandPalette.visible && !paletteFilter.activeFocus
                    sequence: "3"
                    onActivated: {
                        if (win._hasSelection() && controller.currentView === "due") {
                            commandPalette.close()
                            controller.completeTask(win.selectedTaskId, "good")
                        }
                    }
                }
                Shortcut {
                    enabled: commandPalette.visible && !paletteFilter.activeFocus
                    sequence: "4"
                    onActivated: {
                        if (win._hasSelection() && controller.currentView === "due") {
                            commandPalette.close()
                            controller.completeTask(win.selectedTaskId, "easy")
                        }
                    }
                }
                Shortcut {
                    enabled: commandPalette.visible
                    sequence: "Ctrl+S"
                    onActivated: {
                        if (win._hasSelection() && controller.currentView === "due") {
                            commandPalette.close()
                            controller.completeTask(win.selectedTaskId, "good")
                        }
                    }
                }

                contentItem: ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        RowLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                Label {
                                        text: commandPalette.mode === "global" ? "Command Palette" : "Actions"
                                        color: "#E6E6E6"
                                        font.pixelSize: 14
                                }

                                Item { Layout.fillWidth: true }

                                Label {
                                        text: "Ctrl+P"
                                        color: "#7A7A7A"
                                        font.pixelSize: 12
                                }
                        }

                        TextField {
                                id: paletteFilter
                                Layout.fillWidth: true
                                placeholderText: "Type to filter…"
                                onTextChanged: commandPalette.rebuild()
                                Keys.onEscapePressed: commandPalette.close()
                            Keys.onReturnPressed: {
                                commandPalette._runCurrent()
                            }
                            Keys.onEnterPressed: {
                                commandPalette._runCurrent()
                            }
                            Keys.onUpPressed: {
                                if (paletteModel.count <= 0) return
                                listView.currentIndex = Math.max(0, listView.currentIndex - 1)
                                if (listView.positionViewAtIndex) listView.positionViewAtIndex(listView.currentIndex, ListView.Contain)
                            }
                            Keys.onDownPressed: {
                                if (paletteModel.count <= 0) return
                                listView.currentIndex = Math.min(paletteModel.count - 1, listView.currentIndex + 1)
                                if (listView.positionViewAtIndex) listView.positionViewAtIndex(listView.currentIndex, ListView.Contain)
                            }
                        }

                        ListView {
                                id: listView
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                model: paletteModel
                                currentIndex: 0

                                delegate: Rectangle {
                                        required property string group
                                        required property string title
                                        required property string shortcut
                                        required property bool enabled

                                    width: listView.width
                                        height: 42
                                        radius: 10
                                        color: ListView.isCurrentItem ? Qt.rgba(0x3A/255,0x3D/255,0x41/255, 0.75) : "transparent"
                                    clip: true

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.margins: 10
                                            spacing: 10

                                                Label {
                                                        text: group
                                                        color: "#7A7A7A"
                                                        font.pixelSize: 12
                                                        Layout.preferredWidth: 90
                                                        elide: Text.ElideRight
                                                }

                                                Label {
                                                        text: title
                                                        color: enabled ? "#E6E6E6" : "#6E6E6E"
                                                        Layout.fillWidth: true
                                                        elide: Text.ElideRight
                                                }

                                                Label {
                                                        text: shortcut
                                                        color: "#7A7A7A"
                                                        font.pixelSize: 12
                                                        horizontalAlignment: Text.AlignRight
                                                        Layout.preferredWidth: 110
                                                        elide: Text.ElideRight
                                                }
                                        }

                                        MouseArea {
                                                anchors.fill: parent
                                                onClicked: {
                                                        listView.currentIndex = index
                                                        commandPalette._runCurrent()
                                                }
                                        }
                                }

                                Keys.onPressed: (event) => {
                                        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                                                commandPalette._runCurrent()
                                                event.accepted = true
                                        }
                                }
                        }

                        Label {
                                Layout.fillWidth: true
                                text: commandPalette.mode === "context"
                                        ? "Enterで実行 / Escで閉じる"
                                        : "Enterで実行 / Escで閉じる / Shift+F10で選択行アクション"
                                color: "#7A7A7A"
                                font.pixelSize: 12
                        }
                }
        }

    header: Rectangle {
        color: Qt.rgba(0x25/255,0x25/255,0x26/255, 0.82)
        height: 56
        border.color: "#3C3C3C"

        RowLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 12

            Label {
                text: "TaskMaster"
                color: "#E6E6E6"
                font.pixelSize: 18
                Layout.preferredWidth: 220
            }

            TextField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: "Search (title/note) or #tags…"
                onTextChanged: controller.setSearchQuery(text)
                Keys.onEscapePressed: {
                    text = ""
                    controller.setSearchQuery("")
                    tableView.forceActiveFocus()
                }
                background: Rectangle {
                    radius: 10
                    color: Qt.rgba(0x2D/255,0x2D/255,0x30/255, 0.88)
                    border.color: "#3C3C3C"
                }
            }

            RowLayout {
                Layout.preferredWidth: 320
                spacing: 14

                Item {
                    Layout.fillWidth: true
                }

                Label {
                    id: themeLabel
                    text: "Theme: " + controller.theme
                    color: "#BDBDBD"
                    ToolTip.visible: themeMouse.containsMouse
                    ToolTip.text: "View → Theme"
                    MouseArea { id: themeMouse; anchors.fill: parent; hoverEnabled: true }
                }

                Label {
                    id: dbLabel
                    text: "DB: " + controller.dbLabel
                    color: "#BDBDBD"
                    elide: Label.ElideRight
                    ToolTip.visible: dbMouse.containsMouse
                    ToolTip.text: controller.dbTooltip
                    MouseArea { id: dbMouse; anchors.fill: parent; hoverEnabled: true }
                }
            }
        }
    }

    footer: Rectangle {
        height: 28
        color: Qt.rgba(0x25/255,0x25/255,0x26/255, 0.82)
        border.color: "#3C3C3C"

        Text {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 12
            text: controller.statusMessage
            color: "#BDBDBD"
            font.pixelSize: 12
            elide: Text.ElideRight
            width: parent.width - 24
        }
    }

    RowLayout {
        // ApplicationWindow children are laid out in contentItem (header/footer excluded).
        // Anchoring to parent + manual header/footer margins can push content off-screen.
        anchors.fill: win.contentItem

        Rectangle {
            id: sidebar
            Layout.preferredWidth: 220
            Layout.fillHeight: true
            color: Qt.rgba(0x25/255,0x25/255,0x26/255, 0.82)
            border.color: "#3C3C3C"

            ListView {
                id: nav
                anchors.fill: parent
                anchors.margins: 8
                focus: true
                model: [
                    { key: "due", label: "Due", badge: controller.dueCount },
                    { key: "waiting", label: "Waiting", badge: controller.waitingCount },
                    { key: "archived", label: "Archived", badge: -1 },
                    { key: "settings", label: "Settings", badge: -1 }
                ]
                delegate: Rectangle {
                    required property var modelData
                    required property int index

                    width: ListView.view ? ListView.view.width : sidebar.width
                    height: 44
                    radius: 10
                    color: modelData.key === controller.currentView ? Qt.rgba(0x3A/255,0x3D/255,0x41/255, 0.75) : "transparent"

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 8

                        Label {
                            text: modelData.label
                            color: "#E6E6E6"
                            Layout.fillWidth: true
                        }

                        Rectangle {
                            visible: modelData.badge >= 0 && modelData.key !== "settings" && modelData.key !== "archived"
                            radius: 10
                            color: Qt.rgba(0x2D/255,0x2D/255,0x30/255, 0.88)
                            border.color: "#3C3C3C"
                            implicitWidth: 40
                            implicitHeight: 22

                            Label {
                                anchors.centerIn: parent
                                text: modelData.badge
                                color: "#BDBDBD"
                                font.pixelSize: 12
                            }
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            controller.setView(modelData.key)
                            tableView.forceActiveFocus()
                        }
                    }
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: controller.currentView === "settings" ? 1 : 0

            // List (Due/Waiting/Archived)
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 14
                    radius: 12
                    color: Qt.rgba(0x25/255,0x25/255,0x26/255, 0.82)
                    border.color: "#3C3C3C"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 10

                        Label {
                            text: controller.currentView === "due" ? "Due" : controller.currentView === "waiting" ? "Waiting" : "Archived"
                            color: "#E6E6E6"
                            font.pixelSize: 18
                        }

                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            TableView {
                                id: tableView
                                anchors.fill: parent
                                clip: true
                                model: controller.currentView === "due" ? controller.dueModel : controller.currentView === "waiting" ? controller.waitingModel : controller.archivedModel

                                columnWidthProvider: function(col) {
                                    const n = tableView.model ? tableView.model.columnCount() : 1
                                    if (n <= 1) return tableView.width
                                    const first = Math.max(280, tableView.width * 0.35)
                                    if (col === 0) return first
                                    return Math.max(120, (tableView.width - first) / (n - 1))
                                }

                                delegate: Rectangle {
                                    implicitHeight: 36
                                    implicitWidth: 140
                                    color: (win.selectedRow === row) ? Qt.rgba(0x3A/255,0x3D/255,0x41/255, 0.65) : "transparent"
                                    border.color: Qt.rgba(0x3C/255,0x3C/255,0x3C/255, 0.35)

                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        anchors.left: parent.left
                                        anchors.leftMargin: 8
                                        text: display
                                        color: "#E6E6E6"
                                        elide: Text.ElideRight
                                        width: parent.width - 16
                                        font.pixelSize: 13
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                                        onClicked: (mouse) => {
                                            win.selectedRow = row
                                            win.selectedTaskId = tableView.model.taskIdAtRow(row)
                                            if (mouse.button === Qt.RightButton) {
                                                commandPalette.openContextAt(this, mouse.x, mouse.y)
                                            }
                                        }
                                        onDoubleClicked: detailsDialog.openWithSelected(false)
                                    }
                                }

                                Shortcut {
                                    sequence: "Return"
                                    onActivated: detailsDialog.openWithSelected(false)
                                }
                            }

                            // Empty states
                            Item {
                                anchors.fill: parent
                                visible: tableView.model && tableView.model.rowCount() === 0

                                Text {
                                    anchors.centerIn: parent
                                    width: Math.min(parent.width * 0.8, 700)
                                    wrapMode: Text.WordWrap
                                    horizontalAlignment: Text.AlignHCenter
                                    color: "#BDBDBD"
                                    text: controller.currentView === "due"
                                        ? "Dueは0件。Waitingを確認するか、新規タスクを追加してください。"
                                        : controller.currentView === "waiting"
                                            ? "Waitingは0件。Dueのタスクを完了するとここに移動します。"
                                            : "アーカイブは0件。"
                                }
                            }
                        }
                    }
                }
            }

            // Settings
            Rectangle {
                color: "transparent"
                Layout.fillWidth: true
                Layout.fillHeight: true

                Flickable {
                    id: settingsFlick
                    anchors.fill: parent
                    contentWidth: width
                    contentHeight: settingsColumn.implicitHeight + 36
                    clip: true

                    ColumnLayout {
                        id: settingsColumn
                        x: 18
                        y: 18
                        width: Math.max(0, settingsFlick.width - 36)
                        spacing: 14

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: generalCardContent.implicitHeight + 28
                            radius: 12
                            color: Qt.rgba(0x25/255,0x25/255,0x26/255, 0.82)
                            border.color: "#3C3C3C"

                            ColumnLayout {
                                id: generalCardContent
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: 14
                                spacing: 10

                                Label { text: "General"; color: "#E6E6E6"; font.pixelSize: 16 }

                                RowLayout {
                                    Label { text: "Horizon Days"; color: "#BDBDBD"; Layout.preferredWidth: 140 }
                                    SpinBox {
                                        id: horizonBox
                                        from: 1
                                        to: 365
                                        value: controller.horizonDays
                                        editable: true
                                        onValueModified: controller.setHorizonDays(value)
                                    }
                                }

                                RowLayout {
                                    Label { text: "Theme"; color: "#BDBDBD"; Layout.preferredWidth: 140 }
                                    ComboBox {
                                        model: ["light", "dark"]
                                        currentIndex: controller.theme === "dark" ? 1 : 0
                                        onActivated: controller.setTheme(currentText)
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: storageCardContent.implicitHeight + 28
                            radius: 12
                            color: Qt.rgba(0x25/255,0x25/255,0x26/255, 0.82)
                            border.color: "#3C3C3C"

                            ColumnLayout {
                                id: storageCardContent
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: 14
                                spacing: 10

                                Label { text: "Storage"; color: "#E6E6E6"; font.pixelSize: 16 }

                                Label {
                                    text: controller.dbLabel
                                    color: "#BDBDBD"
                                    elide: Text.ElideMiddle
                                }
                                Label {
                                    text: controller.dbTooltip
                                    color: "#7A7A7A"
                                    wrapMode: Text.WordWrap
                                }

                                RowLayout {
                                    Label { text: "DB Path"; color: "#BDBDBD"; Layout.preferredWidth: 140 }
                                    TextField {
                                        id: dbPathField
                                        Layout.fillWidth: true
                                        placeholderText: "/home/yakisenbei/.local/share/taskmaster.db"
                                        text: controller.dbPath
                                    }
                                    Shortcut {
                                        sequence: "Ctrl+S"
                                        onActivated: {
                                            if (win.activeFocusItem === dbPathField) {
                                                controller.setDbPath(dbPathField.text)
                                            }
                                        }
                                    }
                                }

                                RowLayout {
                                    Label { text: "Backup To"; color: "#BDBDBD"; Layout.preferredWidth: 140 }
                                    TextField {
                                        id: backupPathField
                                        Layout.fillWidth: true
                                        placeholderText: "~/backups/taskmaster-backup.db"
                                        text: ""
                                        Component.onCompleted: {
                                            const d = new Date()
                                            function pad(n) { return (n < 10 ? "0" : "") + n }
                                            const stamp = d.getFullYear() + pad(d.getMonth()+1) + pad(d.getDate()) + "-" + pad(d.getHours()) + pad(d.getMinutes())
                                            text = "~/backups/taskmaster-" + stamp + ".db"
                                        }
                                        Keys.onReturnPressed: {
                                            controller.backupDbTo(text)
                                        }
                                    }
                                    Shortcut {
                                        sequence: "Ctrl+B"
                                        onActivated: {
                                            if (win.activeFocusItem === backupPathField) {
                                                controller.backupDbTo(backupPathField.text)
                                            }
                                        }
                                    }
                                }

                                Label {
                                    text: "DB switch: focus DB Path then Ctrl+S. Backup: focus Backup To then Enter/Ctrl+B. Recalculate: Ctrl+Shift+R."
                                    color: "#7A7A7A"
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: newTaskDialog
        modal: true
        focus: true
        x: (win.width - width) / 2
        y: (win.height - height) / 2
        width: 520
        contentItem: Rectangle {
            radius: 12
            color: Qt.rgba(0x2D/255,0x2D/255,0x30/255, 0.88)
            border.color: "#3C3C3C"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                Label { text: "New Task"; color: "#E6E6E6"; font.pixelSize: 16 }

                TextField { id: newTitle; Layout.fillWidth: true; placeholderText: "Title (required)" }
                TextArea { id: newNote; Layout.fillWidth: true; Layout.preferredHeight: 160; placeholderText: "Note" }

                Label { text: "Ctrl+S to save, Esc to cancel"; color: "#7A7A7A" }

                Shortcut {
                    sequence: "Ctrl+S"
                    onActivated: {
                        controller.newTask(newTitle.text, newNote.text)
                        newTaskDialog.close()
                        newTitle.text = ""
                        newNote.text = ""
                    }
                }
                Shortcut {
                    sequence: "Esc"
                    onActivated: {
                        newTaskDialog.close()
                        newTitle.text = ""
                        newNote.text = ""
                    }
                }
            }
        }
    }

    Dialog {
        id: purgeConfirmDialog
        property string taskId: ""

        function openFor(id) {
            taskId = id
            confirmText.text = ""
            open()
            confirmText.forceActiveFocus()
        }

        modal: true
        focus: true
        x: (win.width - width) / 2
        y: (win.height - height) / 2
        width: 460

        contentItem: Rectangle {
            radius: 12
            color: Qt.rgba(0x2D/255,0x2D/255,0x30/255, 0.88)
            border.color: "#3C3C3C"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                Label { text: "Purge (irreversible)"; color: "#E6E6E6"; font.pixelSize: 16 }
                Label { text: "Type 'purge' and press Enter"; color: "#BDBDBD" }

                TextField {
                    id: confirmText
                    Layout.fillWidth: true
                    placeholderText: "purge"
                    Keys.onReturnPressed: {
                        if (text === "purge") {
                            controller.purgeTask(purgeConfirmDialog.taskId)
                            purgeConfirmDialog.close()
                        }
                    }
                    Keys.onEscapePressed: purgeConfirmDialog.close()
                }
            }
        }
    }

    Dialog {
        id: recalcConfirmDialog
        modal: true
        focus: true
        x: (win.width - width) / 2
        y: (win.height - height) / 2
        width: 520

        contentItem: Rectangle {
            radius: 12
            color: Qt.rgba(0x2D/255,0x2D/255,0x30/255, 0.88)
            border.color: "#3C3C3C"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                Label { text: "Recalculate All Tasks"; color: "#E6E6E6"; font.pixelSize: 16 }
                Label { text: "This will reschedule all due/waiting tasks."; color: "#BDBDBD"; wrapMode: Text.WordWrap }
                Label { text: "Press Enter to run, Esc to cancel"; color: "#7A7A7A" }

                Keys.onReturnPressed: {
                    controller.recalculateAll()
                    close()
                }
                Keys.onEscapePressed: close()
            }
        }
    }

    Dialog {
        id: detailsDialog
        property bool editMode: false
        property string taskId: ""

        property var detail: ({})
        property var history: ([])

        function reload() {
            if (!taskId) return
            detail = controller.taskDetail(taskId)
            history = controller.taskHistory(taskId)

            editTitle.text = detail.title ? detail.title : ""
            editNote.text = detail.note ? detail.note : ""

            tagInput.text = ""
            tagListModel.clear()
            if (detail.tags && detail.tags.length) {
                for (let i = 0; i < detail.tags.length; i++) {
                    tagListModel.append({ name: detail.tags[i] })
                }
            }
            historyModel.clear()
            if (history && history.length) {
                for (let j = 0; j < history.length; j++) {
                    historyModel.append(history[j])
                }
            }
        }

        function openWithSelected(edit) {
            if (!win.selectedTaskId) return
            taskId = win.selectedTaskId
            editMode = edit
            open()
            reload()
        }

        modal: true
        focus: true
        padding: 0
        background: Rectangle { color: "transparent" }
        x: (win.width - width) / 2
        y: (win.height - height) / 2
        width: 720
        height: 520

        contentItem: Rectangle {
            id: detailsRoot
            anchors.fill: parent
            radius: 12
            color: Qt.rgba(0x2D/255,0x2D/255,0x30/255, 0.88)
            border.color: "#3C3C3C"
            clip: true

            ListModel { id: tagListModel }
            ListModel { id: historyModel }

            function fmtEpoch(epoch) {
                if (epoch === null || epoch === undefined) return ""
                const d = new Date(epoch * 1000)
                return d.toLocaleString()
            }

            function statusLabel() {
                return detailsDialog.detail && detailsDialog.detail.status ? detailsDialog.detail.status : ""
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                Label { text: detailsDialog.editMode ? "Edit Task" : "Task Details"; color: "#E6E6E6"; font.pixelSize: 16 }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Label {
                        text: "Status: " + detailsRoot.statusLabel()
                        color: "#BDBDBD"
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    Label {
                        text: detailsDialog.taskId
                        color: "#7A7A7A"
                        font.pixelSize: 11
                        elide: Text.ElideMiddle
                        horizontalAlignment: Text.AlignRight
                        Layout.preferredWidth: 260
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Label { text: "Next"; color: "#7A7A7A"; Layout.preferredWidth: 60 }
                    Label {
                        text: detailsRoot.fmtEpoch(detailsDialog.detail.nextReviewAt)
                        color: "#BDBDBD"
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Label { text: "Last"; color: "#7A7A7A"; Layout.preferredWidth: 44 }
                    Label {
                        text: detailsRoot.fmtEpoch(detailsDialog.detail.lastCompletedAt)
                        color: "#BDBDBD"
                        Layout.preferredWidth: 200
                        elide: Text.ElideRight
                    }
                    Label { text: "Count"; color: "#7A7A7A"; Layout.preferredWidth: 54 }
                    Label {
                        text: detailsDialog.detail.reviewCount !== undefined ? detailsDialog.detail.reviewCount : ""
                        color: "#BDBDBD"
                        Layout.preferredWidth: 60
                        horizontalAlignment: Text.AlignRight
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Label { text: "Created"; color: "#7A7A7A"; Layout.preferredWidth: 60 }
                    Label {
                        text: detailsRoot.fmtEpoch(detailsDialog.detail.createdAt)
                        color: "#7A7A7A"
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Label { text: "Updated"; color: "#7A7A7A"; Layout.preferredWidth: 60 }
                    Label {
                        text: detailsRoot.fmtEpoch(detailsDialog.detail.updatedAt)
                        color: "#7A7A7A"
                        Layout.preferredWidth: 220
                        elide: Text.ElideRight
                    }
                }

                ScrollView {
                    id: detailsScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    background: Rectangle { color: "transparent" }

                    ColumnLayout {
                        width: detailsScroll.availableWidth
                        spacing: 10

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 260
                            radius: 12
                            color: Qt.rgba(0x25/255,0x25/255,0x26/255, 0.82)
                            border.color: "#3C3C3C"
                            clip: true

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 10

                                Label { text: "Title"; color: "#BDBDBD" }

                                TextField {
                                    id: editTitle
                                    Layout.fillWidth: true
                                    readOnly: !detailsDialog.editMode
                                    placeholderText: "Title"
                                }

                                Label { text: "Note"; color: "#BDBDBD" }
                                TextArea {
                                    id: editNote
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    readOnly: !detailsDialog.editMode
                                    placeholderText: "Note"
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 170
                            radius: 12
                            color: Qt.rgba(0x25/255,0x25/255,0x26/255, 0.82)
                            border.color: "#3C3C3C"
                            clip: true

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: "Tags"; color: "#E6E6E6"; font.pixelSize: 14 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: "Enter to add, Del to remove"; color: "#7A7A7A"; font.pixelSize: 12 }
                                }

                                TextField {
                                    id: tagInput
                                    Layout.fillWidth: true
                                    placeholderText: "Add tag (e.g. #math)"
                                    enabled: detailsDialog.taskId !== ""
                                    Keys.onReturnPressed: {
                                        let t = (text || "").trim()
                                        if (t.startsWith("#")) t = t.slice(1)
                                        t = t.trim()
                                        if (!t) return
                                        controller.addTag(detailsDialog.taskId, t)
                                        text = ""
                                        detailsDialog.reload()
                                    }
                                }

                                ListView {
                                    id: tagList
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 86
                                    clip: true
                                    model: tagListModel

                                    delegate: Rectangle {
                                        required property string name
                                        height: 30
                                        radius: 8
                                        color: ListView.isCurrentItem ? Qt.rgba(0x3A/255,0x3D/255,0x41/255, 0.75) : "transparent"
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.margins: 6
                                            Label { text: "#" + name; color: "#BDBDBD"; Layout.fillWidth: true; elide: Text.ElideRight }
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            onClicked: tagList.currentIndex = index
                                        }
                                    }

                                    Keys.onDeletePressed: {
                                        if (tagList.currentIndex < 0) return
                                        const row = tagListModel.get(tagList.currentIndex)
                                        controller.removeTag(detailsDialog.taskId, row.name)
                                        detailsDialog.reload()
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 220
                            radius: 12
                            color: Qt.rgba(0x25/255,0x25/255,0x26/255, 0.82)
                            border.color: "#3C3C3C"
                            clip: true

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: "History"; color: "#E6E6E6"; font.pixelSize: 14 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: "Total: " + historyModel.count; color: "#7A7A7A"; font.pixelSize: 12 }
                                }

                                ListView {
                                    id: historyList
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    model: historyModel
                                    delegate: Rectangle {
                                        required property int completedAt
                                        required property string grade
                                        height: 32
                                        color: "transparent"
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.margins: 6
                                            Label {
                                                text: detailsRoot.fmtEpoch(completedAt)
                                                color: "#BDBDBD"
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }
                                            Label {
                                                text: grade
                                                color: "#7A7A7A"
                                                Layout.preferredWidth: 80
                                                horizontalAlignment: Text.AlignRight
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        Label {
                            Layout.fillWidth: true
                            text: detailsDialog.editMode
                                ? "Ctrl+S: save  /  Esc: close"
                                : "F2: edit  /  Ctrl+P: palette  /  Esc: close"
                            color: "#7A7A7A"
                        }
                    }
                }

                Shortcut {
                    sequence: "Esc"
                    onActivated: detailsDialog.close()
                }

                Shortcut {
                    sequence: "F2"
                    onActivated: {
                        detailsDialog.editMode = true
                        editTitle.forceActiveFocus()
                    }
                }

                Shortcut {
                    sequence: "Ctrl+S"
                    onActivated: {
                        if (!detailsDialog.editMode) return
                        controller.editTask(detailsDialog.taskId, editTitle.text, editNote.text)
                        detailsDialog.editMode = false
                        detailsDialog.reload()
                    }
                }

                Shortcut {
                    sequence: "Ctrl+T"
                    onActivated: tagInput.forceActiveFocus()
                }

                Shortcut {
                    sequence: "Ctrl+C"
                    onActivated: {
                        if (detailsDialog.taskId) controller.copyText(detailsDialog.taskId)
                    }
                }
            }
        }
    }
}
