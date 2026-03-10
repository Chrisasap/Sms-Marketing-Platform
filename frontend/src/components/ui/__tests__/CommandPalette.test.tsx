import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import CommandPalette from '../CommandPalette';

function renderPalette() {
  return render(
    <BrowserRouter>
      <CommandPalette />
    </BrowserRouter>
  );
}

describe('CommandPalette', () => {
  it('opens on Ctrl+K', async () => {
    const user = userEvent.setup();
    renderPalette();

    // Palette should not be visible initially
    expect(screen.queryByPlaceholderText('Type a command or search...')).not.toBeInTheDocument();

    // Press Ctrl+K to open
    await user.keyboard('{Control>}k{/Control}');

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Type a command or search...')).toBeInTheDocument();
    });
  });

  it('closes on Escape', async () => {
    const user = userEvent.setup();
    renderPalette();

    // Open the palette
    await user.keyboard('{Control>}k{/Control}');
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Type a command or search...')).toBeInTheDocument();
    });

    // Press Escape to close
    await user.keyboard('{Escape}');

    await waitFor(() => {
      expect(screen.queryByPlaceholderText('Type a command or search...')).not.toBeInTheDocument();
    });
  });

  it('filters commands by query', async () => {
    const user = userEvent.setup();
    renderPalette();

    // Open the palette
    await user.keyboard('{Control>}k{/Control}');
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Type a command or search...')).toBeInTheDocument();
    });

    // All commands should be visible initially
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Campaigns')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();

    // Type a filter query
    const input = screen.getByPlaceholderText('Type a command or search...');
    await user.type(input, 'Campaign');

    // Only Campaign-related items should be visible
    expect(screen.getByText('Campaigns')).toBeInTheDocument();
    expect(screen.getByText('New Campaign')).toBeInTheDocument();
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
    expect(screen.queryByText('Settings')).not.toBeInTheDocument();
  });

  it('shows no results message when nothing matches', async () => {
    const user = userEvent.setup();
    renderPalette();

    await user.keyboard('{Control>}k{/Control}');
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Type a command or search...')).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText('Type a command or search...');
    await user.type(input, 'xyznonexistent');

    expect(screen.getByText('No results found')).toBeInTheDocument();
  });

  it('keyboard navigation with ArrowDown and ArrowUp', async () => {
    const user = userEvent.setup();
    renderPalette();

    await user.keyboard('{Control>}k{/Control}');
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Type a command or search...')).toBeInTheDocument();
    });

    // The first item (Dashboard) should be highlighted by default (activeIndex=0)
    const buttons = screen.getAllByRole('button');
    const dashboardBtn = buttons.find((btn) => btn.textContent?.includes('Dashboard'));
    expect(dashboardBtn).toHaveClass('bg-blue-500/20');

    // Press ArrowDown to move to second item
    const input = screen.getByPlaceholderText('Type a command or search...');
    await user.type(input, '{ArrowDown}');

    // The second item (Campaigns) should now be highlighted
    const campaignsBtn = buttons.find((btn) => btn.textContent?.includes('Campaigns'));
    expect(campaignsBtn).toHaveClass('bg-blue-500/20');
    expect(dashboardBtn).not.toHaveClass('bg-blue-500/20');
  });
});
