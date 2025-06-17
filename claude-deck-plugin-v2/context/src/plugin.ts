import streamDeck, { LogLevel } from "@elgato/streamdeck";
import { CommandAction } from "./actions/command";

// Configure logging
streamDeck.logger.setLevel(LogLevel.DEBUG);

// Register actions
streamDeck.actions.registerAction(new CommandAction());

// Connect to Stream Deck
streamDeck.connect();
