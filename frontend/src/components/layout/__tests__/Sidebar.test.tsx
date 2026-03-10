import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import Sidebar from '../Sidebar';

function renderSidebar() {
  return render(
    <BrowserRouter>
      <Sidebar />
    </BrowserRouter>
  );
}

describe('Sidebar', () => {
  it('renders nav items', () => {
    renderSidebar();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Campaigns')).toBeInTheDocument();
    expect(screen.getByText('Inbox')).toBeInTheDocument();
    expect(screen.getByText('Contacts')).toBeInTheDocument();
    expect(screen.getByText('Numbers')).toBeInTheDocument();
    expect(screen.getByText('Compliance')).toBeInTheDocument();
    expect(screen.getByText('AI Agents')).toBeInTheDocument();
    expect(screen.getByText('Templates')).toBeInTheDocument();
    expect(screen.getByText('Automations')).toBeInTheDocument();
    expect(screen.getByText('Analytics')).toBeInTheDocument();
    expect(screen.getByText('Billing')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('renders BlastWave brand name', () => {
    renderSidebar();
    expect(screen.getByText('BlastWave')).toBeInTheDocument();
  });

  it('collapses sidebar when toggle button is clicked', async () => {
    const user = userEvent.setup();
    renderSidebar();

    // The collapse button is the last button (the one at the bottom)
    // All nav items should be visible when expanded
    expect(screen.getByText('Dashboard')).toBeInTheDocument();

    // Find the collapse toggle button - it's a standalone button, not a link
    const buttons = screen.getAllByRole('button');
    const collapseButton = buttons[buttons.length - 1];

    await user.click(collapseButton);

    // After collapsing, text labels should be hidden via AnimatePresence
    await waitFor(() => {
      // BlastWave text should be removed from the DOM after animation
      expect(screen.queryByText('BlastWave')).not.toBeInTheDocument();
    });
  });

  it('active link is highlighted for current route', () => {
    // Default route is "/" which matches Dashboard
    renderSidebar();

    const dashboardLink = screen.getByText('Dashboard').closest('a');
    expect(dashboardLink).toHaveAttribute('href', '/');
    expect(dashboardLink).toHaveClass('bg-blue-500/10');
    expect(dashboardLink).toHaveClass('text-blue-400');
  });

  it('non-active links have default styling', () => {
    renderSidebar();

    const campaignsLink = screen.getByText('Campaigns').closest('a');
    expect(campaignsLink).toHaveAttribute('href', '/campaigns');
    expect(campaignsLink).toHaveClass('text-gray-400');
    expect(campaignsLink).not.toHaveClass('bg-blue-500/10');
  });

  it('nav items link to correct paths', () => {
    renderSidebar();

    expect(screen.getByText('Dashboard').closest('a')).toHaveAttribute('href', '/');
    expect(screen.getByText('Campaigns').closest('a')).toHaveAttribute('href', '/campaigns');
    expect(screen.getByText('Inbox').closest('a')).toHaveAttribute('href', '/inbox');
    expect(screen.getByText('Contacts').closest('a')).toHaveAttribute('href', '/contacts');
    expect(screen.getByText('Settings').closest('a')).toHaveAttribute('href', '/settings');
  });
});
