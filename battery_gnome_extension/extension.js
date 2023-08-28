// Basic stuff
const St = imports.gi.St;
const Lang = imports.lang;

// UI specific components
const Main = imports.ui.main;
const PopupMenu = imports.ui.popupMenu;
const PanelMenu = imports.ui.panelMenu;
const Mainloop = imports.mainloop;

const Clutter = imports.gi.Clutter;
const GLib = imports.gi.GLib;
const Gio = imports.gi.Gio;

const PERCENTAGEFILEPATH = '/tmp/battery_level';
const plugedEmoji = String.fromCodePoint(0x1F50C);
const batteryEmoji = String.fromCodePoint(0x1F50B);
const TIMER = 2;

function _readPercentageFromFile() {
    try {
        let file = Gio.File.new_for_path(PERCENTAGEFILEPATH);
        let [, content] = file.load_contents(null);
        let read = content.toString().trim();

        const letter = read.substring(0, 1);
        const number = parseInt(read.substring(1));
        return [letter, number];
    } catch (e) {
        logError(e, 'Error reading percentage file');
        return ['-', '---'];
    }
}


const Indicator = new Lang.Class({
    Name: 'GnomeBitBarIndicator', // TODO does this even matter?
    Extends: PanelMenu.Button,

    _init: function() {
        this.parent(0.0, "GnomeBitBar", false); // TODO does this even matter?

        // Set up click handlers
        this.actor.connect('enter_event', Lang.bind(this, this.resetCounter, true));
        this.actor.connect('leave_event', Lang.bind(this, this.resetCounter, false));
        this.actor.connect('button_press_event', Lang.bind(this, this.resetCounter, false));

        this.text = new St.Label({
            text: "loading..."
        });
        this._refresh();
        this.actor.add_actor(this.text);
    },

    resetCounter: function(){
        return true;
    },

    updateUI: function() {
        const battery = _readPercentageFromFile();
        if(battery[0] == 'C'){
            this.text.set_text(`${plugedEmoji} ${battery[1]}%`);
        }
        else if(battery[0] == 'D'){
            this.text.set_text(`${batteryEmoji}  ${battery[1]}%`);
        }
        else{
            this.text.set_text(` ${battery[0]} - ${battery[1]}%`);
        }
    },

    _refresh: function () {
        this.updateUI();
        this._removeTimeout();
        this._timeout = Mainloop.timeout_add_seconds(TIMER, Lang.bind(this, this._refresh));
        return true;
    },

    _removeTimeout: function () {
        if (this._timeout) {
            Mainloop.source_remove(this._timeout);
            this._timeout = null;
        }
    }
});

let menu;

function init() {
    // One time startup initialization
}

function enable() {
    menu = new Indicator();
    Main.panel.addToStatusArea('indicator', menu);
}

function disable() {
    menu.destroy();
}
