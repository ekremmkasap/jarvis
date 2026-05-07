const { BrowserWindow, screen } = require("electron");
const path = require("path");

const AGENTS = [
    { id: "seda",     align: "right", yIndex: 0 },
    { id: "mert",     align: "right", yIndex: 1 },
    { id: "buse",     align: "right", yIndex: 2 },
    { id: "eren",     align: "right", yIndex: 3 },
    { id: "luna",     align: "left",  yIndex: 0 },
    { id: "sabrican", align: "left",  yIndex: 1 },
    { id: "sabri",    align: "left",  yIndex: 2 },
];

const WINDOW_WIDTH = 200;
const WINDOW_HEIGHT = 280;
const SPACING_Y = 290;

let swarmWindows = {};

function launchSwarmWindows() {
    const displays = screen.getAllDisplays();
    const primaryDisplay = screen.getPrimaryDisplay();
    // Use second display if available for left alignment, otherwise primary
    const secondaryDisplay = displays.length > 1 ? displays[1] : primaryDisplay;

    AGENTS.forEach(agent => {
        const display = agent.align === "left" ? secondaryDisplay : primaryDisplay;
        const workArea = display.workArea;

        let x = 0;
        let y = workArea.y + (agent.yIndex * SPACING_Y);

        if (agent.align === "right") {
            x = workArea.x + workArea.width - WINDOW_WIDTH - 20;
        } else {
            // left align
            x = workArea.x + 20;
        }

        // prevent overflow
        if (y + WINDOW_HEIGHT > workArea.y + workArea.height) {
            y = workArea.y + workArea.height - WINDOW_HEIGHT - 10;
        }

        const win = new BrowserWindow({
            width: WINDOW_WIDTH,
            height: WINDOW_HEIGHT,
            x: x,
            y: y,
            transparent: true,
            frame: false,
            alwaysOnTop: true,
            skipTaskbar: true,
            resizable: false,
            webPreferences: {
                nodeIntegration: true,
                contextIsolation: false
            }
        });

        win.loadFile(path.join(__dirname, `swarm_${agent.id}.html`)).catch(() => {
            // fallback if individual html is missing, use a generic one
            win.loadFile(path.join(__dirname, `swarm_generic.html`));
            win.webContents.on('did-finish-load', () => {
                win.webContents.send('set-agent', agent.id);
            });
        });

        swarmWindows[agent.id] = win;
    });
}

function closeSwarmWindows() {
    Object.values(swarmWindows).forEach(win => {
        if (!win.isDestroyed()) {
            win.close();
        }
    });
    swarmWindows = {};
}

module.exports = {
    launchSwarmWindows,
    closeSwarmWindows
};
