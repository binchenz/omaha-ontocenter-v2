/**
 * DataTable component - displays query results in a table.
 */
import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
} from '@mui/material';

interface DataTableProps {
  data: Record<string, any>[];
}

export const DataTable: React.FC<DataTableProps> = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No data to display
      </Typography>
    );
  }

  const columns = Object.keys(data[0]);

  return (
    <TableContainer component={Paper} sx={{ maxHeight: 400, mt: 2 }}>
      <Table stickyHeader size="small">
        <TableHead>
          <TableRow>
            {columns.map((column) => (
              <TableCell key={column} sx={{ fontWeight: 'bold' }}>
                {column}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {data.map((row, index) => (
            <TableRow key={index} hover>
              {columns.map((column) => (
                <TableCell key={column}>
                  {row[column] !== null && row[column] !== undefined
                    ? String(row[column])
                    : '-'}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};
