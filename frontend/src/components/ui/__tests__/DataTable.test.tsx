import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DataTable from '../DataTable';

const columns = [
  { key: 'name', label: 'Name', sortable: true },
  { key: 'email', label: 'Email', sortable: true },
  { key: 'status', label: 'Status' },
];

function makeData(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    name: `User ${i + 1}`,
    email: `user${i + 1}@example.com`,
    status: i % 2 === 0 ? 'Active' : 'Inactive',
  }));
}

describe('DataTable', () => {
  it('renders data rows', () => {
    const data = makeData(3);
    render(<DataTable data={data} columns={columns} />);
    expect(screen.getByText('User 1')).toBeInTheDocument();
    expect(screen.getByText('User 2')).toBeInTheDocument();
    expect(screen.getByText('User 3')).toBeInTheDocument();
    expect(screen.getByText('user1@example.com')).toBeInTheDocument();
  });

  it('search filters results', async () => {
    const user = userEvent.setup();
    const data = makeData(5);
    render(<DataTable data={data} columns={columns} />);

    const searchInput = screen.getByPlaceholderText('Search...');
    await user.type(searchInput, 'User 3');

    expect(screen.getByText('User 3')).toBeInTheDocument();
    expect(screen.queryByText('User 1')).not.toBeInTheDocument();
    expect(screen.queryByText('User 2')).not.toBeInTheDocument();
  });

  it('sort by column', async () => {
    const user = userEvent.setup();
    const data = [
      { name: 'Charlie', email: 'c@test.com', status: 'Active' },
      { name: 'Alice', email: 'a@test.com', status: 'Active' },
      { name: 'Bob', email: 'b@test.com', status: 'Active' },
    ];
    render(<DataTable data={data} columns={columns} />);

    // Click Name header to sort ascending
    await user.click(screen.getByText('Name'));

    const cells = screen.getAllByRole('cell');
    const nameValues = cells
      .filter((_, i) => i % columns.length === 0)
      .map((el) => el.textContent);
    expect(nameValues).toEqual(['Alice', 'Bob', 'Charlie']);
  });

  it('pagination works', async () => {
    const user = userEvent.setup();
    const data = makeData(25);
    render(<DataTable data={data} columns={columns} pageSize={10} />);

    // Should show first page results
    expect(screen.getByText('User 1')).toBeInTheDocument();
    expect(screen.getByText('User 10')).toBeInTheDocument();
    expect(screen.queryByText('User 11')).not.toBeInTheDocument();

    // Shows result count and page info
    expect(screen.getByText('25 results')).toBeInTheDocument();
    expect(screen.getByText('Page 1 of 3')).toBeInTheDocument();

    // Navigate to next page
    await user.click(screen.getByText('Next'));
    expect(screen.getByText('User 11')).toBeInTheDocument();
    expect(screen.getByText('Page 2 of 3')).toBeInTheDocument();

    // Navigate back
    await user.click(screen.getByText('Prev'));
    expect(screen.getByText('User 1')).toBeInTheDocument();
    expect(screen.getByText('Page 1 of 3')).toBeInTheDocument();
  });

  it('row selection', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const data = makeData(3);
    render(<DataTable data={data} columns={columns} selectable onSelect={onSelect} />);

    const checkboxes = screen.getAllByRole('checkbox');
    // First checkbox is the "select all" header checkbox, rest are row checkboxes
    expect(checkboxes).toHaveLength(4); // 1 header + 3 rows

    // Select first row
    await user.click(checkboxes[1]);
    expect(onSelect).toHaveBeenCalledWith([data[0]]);

    // Select all via header checkbox
    await user.click(checkboxes[0]);
    expect(onSelect).toHaveBeenCalledWith(data);
  });
});
