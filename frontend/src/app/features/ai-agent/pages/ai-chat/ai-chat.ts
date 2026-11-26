import { Component, OnDestroy, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AiAgentService } from '../../services/ai-agent.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { ProposalCard } from '../../components/proposal-card/proposal-card';
import { Icon } from '../../../../shared/components/icon/icon';
import { AiThinking } from '../../components/ai-thinking/ai-thinking';

/** Un mensaje de voz dura como máximo un minuto: luego se detiene y se envía. */
export const MAX_RECORDING_MS = 60_000;

@Component({
  selector: 'app-ai-chat',
  imports: [FormsModule, PageHeader, Button, ProposalCard, Icon, AiThinking],
  templateUrl: './ai-chat.html',
  styleUrl: './ai-chat.scss',
})
/** Un mensaje de voz dura como máximo un minuto: luego se detiene y se envía. */
export class AiChat implements OnDestroy {
  aiAgent = inject(AiAgentService);

  draft = signal('');
  sending = signal(false);
  recording = signal(false);

  #recorder: MediaRecorder | null = null;
  #stopTimer: ReturnType<typeof setTimeout> | undefined;
  #discard = false;

  interactionFor(interactionId: string | undefined) {
    if (!interactionId) return null;
    return this.aiAgent.interactions().find((i) => i.id === interactionId) ?? null;
  }

  send(): void {
    const text = this.draft().trim();
    if (!text || this.sending()) return;

    this.sending.set(true);
    this.draft.set('');
    this.aiAgent.send(text).subscribe(() => this.sending.set(false));
  }

  /** Envía la foto; lo escrito en el cuadro de texto la acompaña como indicación. */
  uploadImage(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = ''; // permite volver a elegir la misma foto
    if (!file || this.sending()) return;

    this.sending.set(true);
    const caption = this.draft();
    this.draft.set('');
    this.aiAgent.sendImage(file, caption).subscribe(() => this.sending.set(false));
  }

  /** Primer toque: empieza a grabar. Segundo toque (o al minuto): detiene y envía. */
  async toggleRecording(): Promise<void> {
    if (this.recording()) {
      this.#recorder?.stop();
      return;
    }
    if (this.sending()) return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      this.aiAgent.notify('Este navegador no permite grabar audio. Escribe el mensaje.');
      return;
    }

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      this.aiAgent.notify('No pude usar el micrófono. Revisa el permiso del navegador para este sitio.');
      return;
    }

    const recorder = new MediaRecorder(stream);
    const chunks: Blob[] = [];
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data);
    };
    recorder.onstop = () => {
      clearTimeout(this.#stopTimer);
      stream.getTracks().forEach((track) => track.stop());
      this.#recorder = null;
      this.recording.set(false);
      const audio = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
      if (this.#discard || audio.size === 0) return;

      this.sending.set(true);
      this.aiAgent.sendAudio(audio).subscribe(() => this.sending.set(false));
    };

    this.#discard = false;
    this.#recorder = recorder;
    recorder.start();
    this.recording.set(true);
    this.#stopTimer = setTimeout(() => recorder.stop(), MAX_RECORDING_MS);
  }

  /** Al salir de la página se descarta lo que se estaba grabando y se libera el micrófono. */
  ngOnDestroy(): void {
    this.#discard = true;
    if (this.#recorder?.state === 'recording') this.#recorder.stop();
  }
}
