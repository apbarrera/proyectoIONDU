import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ToastContainer } from './shared/components/toast-container/toast-container';
import { ConfirmDialog } from './shared/components/confirm-dialog/confirm-dialog';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, ToastContainer, ConfirmDialog],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {}
