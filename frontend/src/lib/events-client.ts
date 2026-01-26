export class AppSyncEventsClient {
  private ws: WebSocket | null = null;
  private subscriptions: Map<string, (data: any) => void> = new Map();
  private isConnected = false;

  constructor(private endpoint: string, private apiKey: string) {}

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.endpoint);

        this.ws.onopen = () => {
          this.isConnected = true;
          this.send({
            type: 'connection_init',
            payload: { 'x-api-key': this.apiKey },
          });
          resolve();
        };

        this.ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.type === 'data') {
            const callback = this.subscriptions.get(data.payload.channel);
            if (callback) callback(data.payload);
          }
        };

        this.ws.onerror = reject;
        this.ws.onclose = () => {
          this.isConnected = false;
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  subscribe(channel: string, callback: (data: any) => void): void {
    this.subscriptions.set(channel, callback);
    if (this.isConnected && this.ws) {
      this.send({ type: 'subscribe', payload: { channel } });
    }
  }

  unsubscribe(channel: string): void {
    this.subscriptions.delete(channel);
    if (this.isConnected && this.ws) {
      this.send({ type: 'unsubscribe', payload: { channel } });
    }
  }

  disconnect(): void {
    if (this.ws) this.ws.close();
    this.subscriptions.clear();
    this.isConnected = false;
  }

  private send(message: any): void {
    if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  isConnectedStatus(): boolean {
    return this.isConnected;
  }
}

let eventsClient: AppSyncEventsClient | null = null;

export function getEventsClient(): AppSyncEventsClient {
  if (!eventsClient) {
    const endpoint = process.env.NEXT_PUBLIC_APPSYNC_EVENTS_ENDPOINT || '';
    const apiKey = process.env.NEXT_PUBLIC_APPSYNC_EVENTS_API_KEY || '';
    eventsClient = new AppSyncEventsClient(endpoint, apiKey);
  }
  return eventsClient;
}