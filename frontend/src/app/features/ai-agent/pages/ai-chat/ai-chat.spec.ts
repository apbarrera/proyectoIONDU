import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { afterEach, vi } from 'vitest';

import { AiChat } from './ai-chat';
import { AiAgentService } from '../../services/ai-agent.service';

/** Grabadora simulada: al detenerse entrega un trozo de audio, como el navegador. */
class FakeMediaRecorder {
  static last: FakeMediaRecorder | null = null;
  state: 'inactive' | 'recording' = 'inactive';
  mimeType = 'audio/webm;codecs=opus';
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;

  constructor(public stream: MediaStream) {
    FakeMediaRecorder.last = this;
  }

  start(): void {
    this.state = 'recording';
  }

  stop(): void {
    this.state = 'inactive';
    this.ondataavailable?.({ data: new Blob([new Uint8Array([0x1a, 0x45, 0xdf, 0xa3])]) });
    this.onstop?.();
  }
}

describe('AiChat', () => {
  let component: AiChat;
  let fixture: ComponentFixture<AiChat>;
  let http: HttpTestingController;
  const track = { stop: vi.fn() };
  const getUserMedia = vi.fn();

  beforeEach(async () => {
    track.stop.mockClear();
    getUserMedia.mockReset().mockResolvedValue({ getTracks: () => [track] });
    vi.stubGlobal('MediaRecorder', FakeMediaRecorder);
    Object.defineProperty(navigator, 'mediaDevices', { value: { getUserMedia }, configurable: true });

    await TestBed.configureTestingModule({
      imports: [AiChat],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(AiChat);
    component = fixture.componentInstance;
    http = TestBed.inject(HttpTestingController);
    await fixture.whenStable();
  });

  afterEach(() => {
    http.verify();
    vi.unstubAllGlobals();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('grabar y volver a tocar envía el audio y libera el micrófono', async () => {
    await component.toggleRecording();
    expect(component.recording()).toBe(true);

    await component.toggleRecording();

    expect(component.recording()).toBe(false);
    expect(track.stop).toHaveBeenCalled();
    expect(component.sending()).toBe(true);
    http
      .expectOne({ method: 'POST', url: '/api/ai/audio' })
      .flush({ actionId: null, reply: 'No logré entender el audio.', proposal: null, transcript: '' });
    expect(component.sending()).toBe(false);
  });

  it('sin permiso de micrófono avisa y no envía nada', async () => {
    getUserMedia.mockRejectedValue(new DOMException('denegado', 'NotAllowedError'));

    await component.toggleRecording();

    expect(component.recording()).toBe(false);
    const messages = TestBed.inject(AiAgentService).messages();
    expect(messages.at(-1)?.content).toContain('micrófono');
    http.expectNone('/api/ai/audio');
  });

  it('salir de la página mientras graba descarta el audio', async () => {
    await component.toggleRecording();

    fixture.destroy();

    expect(FakeMediaRecorder.last?.state).toBe('inactive');
    expect(track.stop).toHaveBeenCalled();
    http.expectNone('/api/ai/audio');
  });
});
