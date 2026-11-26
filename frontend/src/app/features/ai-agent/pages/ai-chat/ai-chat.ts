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

  uploadImage(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    this.aiAgent.send(`Imagen: ${file.name}`, 'imagen', [{ type: 'image', url, name: file.name }]).subscribe();
  }

  toggleRecording(): void {
    this.aiAgent.send('Mensaje de voz', 'voz').subscribe();
  }
}
