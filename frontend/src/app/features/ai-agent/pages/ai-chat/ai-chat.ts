import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AiAgentService } from '../../services/ai-agent.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { ProposalCard } from '../../components/proposal-card/proposal-card';
import { Icon } from '../../../../shared/components/icon/icon';

@Component({
  selector: 'app-ai-chat',
  imports: [FormsModule, PageHeader, Button, ProposalCard, Icon],
  templateUrl: './ai-chat.html',
  styleUrl: './ai-chat.scss',
})
export class AiChat {
  aiAgent = inject(AiAgentService);

  draft = signal('');
  sending = signal(false);
  recording = signal(false); // se usará con la entrada por voz

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

  toggleRecording(): void {
    this.aiAgent.send('Mensaje de voz', 'voz').subscribe();
  }
}
