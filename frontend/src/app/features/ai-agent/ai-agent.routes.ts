import { Routes } from '@angular/router';
import { AiChat } from './pages/ai-chat/ai-chat';
import { AiHistory } from './pages/ai-history/ai-history';

export const AI_AGENT_ROUTES: Routes = [
  { path: '', component: AiChat },
  { path: 'history', component: AiHistory },
];
