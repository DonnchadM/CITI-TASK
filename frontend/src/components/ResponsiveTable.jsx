import { useMediaQuery } from 'react-responsive';
import {
  Box, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Typography,
} from '@mui/material';

// Generic list renderer: a data table on desktop, a stack of cards on mobile
// (react-responsive content swap). `columns` is [{ key, label, align, render }];
// `renderActions(row)` and `renderCard(row)` are optional.
export function ResponsiveTable({
  columns, rows, getRowKey, renderActions, renderCard, emptyText = 'No records found.',
}) {
  const isMobile = useMediaQuery({ maxWidth: 600 });

  if (!rows.length) {
    return <Typography color="text.secondary" sx={{ mt: 2 }}>{emptyText}</Typography>;
  }

  if (isMobile && renderCard) {
    return (
      <Stack spacing={2}>
        {rows.map((row) => (
          <Box key={getRowKey(row)}>{renderCard(row)}</Box>
        ))}
      </Stack>
    );
  }

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            {columns.map((col) => (
              <TableCell key={col.key} align={col.align}>{col.label}</TableCell>
            ))}
            {renderActions && <TableCell align="right">Actions</TableCell>}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={getRowKey(row)} hover>
              {columns.map((col) => (
                <TableCell key={col.key} align={col.align}>
                  {col.render ? col.render(row) : row[col.key]}
                </TableCell>
              ))}
              {renderActions && <TableCell align="right">{renderActions(row)}</TableCell>}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
