import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PercentIcon from '@mui/icons-material/Percent';
import { KpiCard } from './KpiCard';

describe('<KpiCard>', () => {
  it('renders the label and value', () => {
    render(<KpiCard label="Teams tracked" value={5} icon={<PercentIcon />} />);
    expect(screen.getByText('Teams tracked')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });
});
