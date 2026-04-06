import { BridgeCommand } from "../contracts/BridgeCommand";
import { Skill } from "./Skill";

type BridgeResponse = {
  ok?: boolean;
  result?: unknown;
  error?: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export class BridgeSkill implements Skill {
  readonly id = "bridge";
  readonly version = "1";
  readonly status = "APPROVED" as const;
  readonly manifest = {
    permissions: []
  };

  constructor(private readonly bridgeUrl = process.env.BRIDGE_URL ?? "http://127.0.0.1:8081") {}

  async run(input: unknown): Promise<unknown> {
    const payload = this.toBridgeCommand(input);
    const response = await fetch(new URL("/command", this.bridgeUrl).toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
    const body = await this.parseResponse(response);

    if (!response.ok) {
      throw new Error(`BRIDGE_HTTP_${response.status}:${this.extractError(body)}`);
    }
    if (!body.ok) {
      throw new Error(`BRIDGE_COMMAND_FAILED:${this.extractError(body)}`);
    }

    return body.result;
  }

  private toBridgeCommand(input: unknown): BridgeCommand {
    if (!isRecord(input)) {
      throw new Error("BRIDGE_COMMAND_INVALID: input must be an object");
    }

    const command = input.command;
    if (typeof command !== "string" || !command.trim()) {
      throw new Error("BRIDGE_COMMAND_INVALID: command must be a non-empty string");
    }

    const args = input.args;
    if (args !== undefined && !isRecord(args)) {
      throw new Error("BRIDGE_COMMAND_INVALID: args must be an object when provided");
    }

    const chatId = input.chatId;
    if (chatId !== undefined && typeof chatId !== "string") {
      throw new Error("BRIDGE_COMMAND_INVALID: chatId must be a string when provided");
    }

    return {
      command: command.trim(),
      args,
      chatId
    };
  }

  private async parseResponse(response: Response): Promise<BridgeResponse> {
    const raw = await response.text();
    if (!raw) {
      return {};
    }

    try {
      return JSON.parse(raw) as BridgeResponse;
    } catch {
      throw new Error(`BRIDGE_INVALID_JSON:${raw.slice(0, 200)}`);
    }
  }

  private extractError(body: BridgeResponse): string {
    if (typeof body.error === "string" && body.error) {
      return body.error;
    }
    return "Unknown bridge error";
  }
}

export const bridgeSkill = new BridgeSkill();
