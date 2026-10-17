export interface AiConfig {
  instructions: string;
  allowedActions: string[];
  forbiddenActions: string[];
  askForMoreInfoWhenUncertain: boolean;
  monthlyTokenLimit: number;
}
