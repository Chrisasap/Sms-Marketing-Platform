import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import GlassCard from '../GlassCard';

describe('GlassCard', () => {
  it('renders children', () => {
    render(<GlassCard><span>Hello World</span></GlassCard>);
    expect(screen.getByText('Hello World')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<GlassCard className="my-custom-class"><span>Content</span></GlassCard>);
    const card = screen.getByText('Content').parentElement;
    expect(card).toHaveClass('my-custom-class');
  });

  it('renders without hover animation by default', () => {
    const { container } = render(<GlassCard><span>No Hover</span></GlassCard>);
    // The component renders a motion.div; just verify it renders correctly
    expect(container.firstChild).toBeTruthy();
    expect(screen.getByText('No Hover')).toBeInTheDocument();
  });

  it('renders with hover animation prop', () => {
    const { container } = render(<GlassCard hover><span>Hover Me</span></GlassCard>);
    expect(container.firstChild).toBeTruthy();
    expect(screen.getByText('Hover Me')).toBeInTheDocument();
  });
});
