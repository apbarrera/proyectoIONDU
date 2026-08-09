import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Header } from '../header/header';
import { Sidebar } from '../sidebar/sidebar';
import { FloatingAiPanel } from '../../../features/ai-agent/components/floating-ai-panel/floating-ai-panel';

@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, Header, Sidebar, FloatingAiPanel],
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
})
export class Shell {
  mobileNavOpen = signal(false);

  toggleMobileNav(): void {
    this.mobileNavOpen.update((v) => !v);
  }

  closeMobileNav(): void {
    this.mobileNavOpen.set(false);
  }
}
