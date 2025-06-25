import streamDeck, { LogLevel } from "@elgato/streamdeck";
import { CommandAction } from "./actions/command";
import { OkAction } from "./actions/ok";
import { EscapeAction } from "./actions/escape";
import { ShiftTabAction } from "./actions/shift-tab";
import { ModelAction } from "./actions/model";

// Configure logging
streamDeck.logger.setLevel(LogLevel.DEBUG);

// Register actions
streamDeck.actions.registerAction(new CommandAction());
streamDeck.actions.registerAction(new OkAction());
streamDeck.actions.registerAction(new EscapeAction());
streamDeck.actions.registerAction(new ShiftTabAction());
streamDeck.actions.registerAction(new ModelAction());

// Connect to Stream Deck
streamDeck.connect();
