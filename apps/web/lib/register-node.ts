import { publicCommandError } from "@pdoom/db";
import { bootServer } from "./boot";

export function registerNode(): void {
  try {
    bootServer();
  } catch (error) {
    console.error(publicCommandError(error));
    process.exit(1);
  }
}
