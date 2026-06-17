import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AuthContext } from '../context/auth-context';
import { Can } from './Can';

function renderAs(role, ui) {
  return render(<AuthContext.Provider value={{ user: { role } }}>{ui}</AuthContext.Provider>);
}

describe('<Can>', () => {
  it('renders children when the role permits the action', () => {
    renderAs('ADMIN', <Can action="delete"><button>Delete</button></Can>);
    expect(screen.getByText('Delete')).toBeInTheDocument();
  });

  it('renders nothing when the role lacks the permission', () => {
    renderAs('VIEWER', <Can action="delete"><button>Delete</button></Can>);
    expect(screen.queryByText('Delete')).toBeNull();
  });

  it('renders the fallback when provided and not permitted', () => {
    renderAs('VIEWER', <Can action="create" fallback={<span>locked</span>}><button>Add</button></Can>);
    expect(screen.queryByText('Add')).toBeNull();
    expect(screen.getByText('locked')).toBeInTheDocument();
  });
});
