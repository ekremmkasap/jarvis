export interface BridgeCommand {
  command: string;
  args?: Record<string, unknown>;
  chatId?: string;
}
