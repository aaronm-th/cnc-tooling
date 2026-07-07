import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'

/**
 * Generiert einen Arbeitsstunden-Report im klassischen Schreibmaschinen-Stil.
 * Garantiert das Layout auf genau einer DIN-A4-Seite.
 */
export const generateWorkingHoursPDF = async (data) => {
  // Wir packen die neuen monatlichen Gesamtsummen direkt mit aus!
  const { monthName, year, userName, events, monthly_soll, monthly_ist, monthly_diff } = data
  
  // A4-Format initialisieren (Ein-Seiten-Sicherheits-Layout)
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  })
  
  const today = new Date().toLocaleDateString('de-DE')
  
  // --- 1. Globalen Font auf Courier setzen (Schreibmaschine) ---
  doc.setFont('courier', 'normal')

  // --- 2. Header (Altmodischer Stempel-Stil) ---
  doc.setFontSize(16)
  doc.setFont('courier', 'bold')
  doc.setTextColor(0, 0, 0)
  doc.text('ZEITNACHWEIS', 15, 20)
  
  doc.setFontSize(9)
  doc.setFont('courier', 'normal')
  doc.text('Personalwesen / Arbeitszeiterfassung', 15, 25)
  
  // Gestrichelte Trennlinie im Schreibmaschinen-Stil
  doc.setLineWidth(0.2)
  doc.setDrawColor(0, 0, 0)
  doc.line(15, 28, 195, 28)

  // --- 3. Info-Block Links (Mitarbeiterdaten) ---
  doc.setFontSize(9)
  
  doc.setFont('courier', 'bold')
  doc.text('MITARBEITER:', 15, 36)
  doc.setFont('courier', 'normal')
  doc.text(`${(userName || 'Mitarbeiter').toUpperCase()}`, 48, 36)
  
  doc.setFont('courier', 'bold')
  doc.text('ZEITRAUM:', 15, 41)
  doc.setFont('courier', 'normal')
  doc.text(`${(monthName || '').toUpperCase()} ${year}`, 48, 41)
  
  doc.setFont('courier', 'bold')
  doc.text('AUSGESTELLT:', 15, 46)
  doc.setFont('courier', 'normal')
  doc.text(today, 48, 46)

  // --- NEU: Info-Block Rechts (Monats-Statistiken / Zusammenfassung) ---
  // Platziert auf der rechten Seite (X=140), damit das Dokument offizieller wirkt
  doc.setFont('courier', 'bold')
  doc.text('SOLL-MONAT:', 140, 36)
  doc.setFont('courier', 'normal')
  doc.text(`${parseFloat(monthly_soll || 0).toFixed(2)} h`, 172, 36)

  doc.setFont('courier', 'bold')
  doc.text('IST-MONAT:', 140, 41)
  doc.setFont('courier', 'normal')
  doc.text(`${parseFloat(monthly_ist || 0).toFixed(2)} h`, 172, 41)

  doc.setFont('courier', 'bold')
  doc.text('MONATS-BALO:', 140, 46)
  doc.setFont('courier', 'normal')
  const totalDiffNum = parseFloat(monthly_diff || 0)
  const totalPrefix = totalDiffNum > 0 ? '+' : ''
  doc.text(`${totalPrefix}${totalDiffNum.toFixed(2)} h`, 172, 46)

  // --- 4. Datenaufbereitung für das Tabellen-Raster ---
  const tableData = (events || []).map(day => {
    const dateObj = new Date(day.date); 
    
    const germanDate = dateObj.toLocaleDateString('de-DE', {
      weekday: 'short',
      day: '2-digit',
      month: '2-digit'
    }).replace('.', '');

    // Tages-Saldo formatieren (Wenn > 0, ein "+" voranstellen)
    const dayDiffNum = parseFloat(day.diff || 0)
    let diffStr = '0.00 h'
    if (dayDiffNum > 0) {
      diffStr = `+${dayDiffNum.toFixed(2)} h`
    } else if (dayDiffNum < 0) {
      diffStr = `${dayDiffNum.toFixed(2)} h` // Das Minuszeichen liefert toFixed automatisch
    }

    return [
      germanDate,
      day.day_type_display ? day.day_type_display.toUpperCase() : 'ARBEITSTAG',
      day.actual_hours ? `${parseFloat(day.actual_hours).toFixed(2)} h` : '0.00 h',
      diffStr, // Das berechnete Tages-Saldo (Abweichung von der Soll-Arbeitszeit)
      day.session_details || '-'
    ];
  });

  // --- 5. Tabelle im echten Schreibmaschinen-Gitterraster ---
  autoTable(doc, {
    startY: 52,
    margin: { left: 15, right: 15 },
    head: [['DATUM', 'STATUS / TYP', 'GEARBEITET', 'SALDO', 'ZEITRÄUME']],
    body: tableData,
    theme: 'grid', // Striktes Gitternetz
    styles: { 
      font: 'courier',
      fontSize: 8, 
      cellPadding: 1.2, // Komprimiert, damit es sicher auf 1 Seite passt
      textColor: [0, 0, 0],
      lineColor: [0, 0, 0], // Schwarze Linien
      lineWidth: 0.1,
      valign: 'middle'
    },
    headStyles: { 
      fillColor: [240, 240, 240], // Sehr dezentes Grau für den Header
      textColor: [0, 0, 0],
      fontStyle: 'bold',
      lineWidth: 0.2,
      halign: 'left'
    },
    columnStyles: {
      0: { cellWidth: 22 },
      1: { cellWidth: 32 },
      2: { cellWidth: 25, halign: 'right' },
      3: { cellWidth: 22, halign: 'right' },
      4: { cellWidth: 'auto' }
    },
    didParseCell: function(data) {
      if (data.section === 'body') {
        const rowIndex = data.row.index
        const rawDay = events[rowIndex]

        if (rawDay) {
          // Wochenenden & Feiertage leicht ausgrauen
          if (['weekend', 'holiday'].includes(rawDay.day_type)) {
            data.cell.styles.textColor = [120, 120, 120]
          }
          
          // Negative Salden (Minus-Stunden) in der Saldo-Spalte (Index 3) klassisch rot markieren
          if (data.column.index === 3 && parseFloat(rawDay.diff) < 0) {
            data.cell.styles.textColor = [180, 0, 0]
          }
          // Positive Salden (Überstunden) dezent dunkelgrün markieren
          if (data.column.index === 3 && parseFloat(rawDay.diff) > 0) {
            data.cell.styles.textColor = [0, 100, 0]
          }

          // Urlaub & Krankheit fett hervorheben
          if (['vacation', 'leave', 'sick'].includes(rawDay.day_type)) {
            data.cell.styles.fontStyle = 'bold'
          }
        }
      }
    }
  })

  // --- 6. Zusammenfassung & Abschluss ---
  const finalY = doc.lastAutoTable.finalY + 8
  
  doc.setFontSize(10)
  doc.setFont('courier', 'bold')
  
  // Formatierung des Gesamtsaldos (Basiert nun wasserdicht auf dem Backend-Wert)
  const finalDiffNum = parseFloat(monthly_diff || 0)
  const finalPrefix = finalDiffNum > 0 ? '+' : ''
  const balanceText = `GESAMT-SALDO MONAT: ${finalPrefix}${finalDiffNum.toFixed(2)} h`
  
  if (finalDiffNum < 0) {
    doc.setTextColor(180, 0, 0) // Rot bei Gesamt-Minus
  } else if (finalDiffNum > 0) {
    doc.setTextColor(0, 100, 0) // Dunkelgrün bei Gesamt-Plus
  } else {
    doc.setTextColor(0, 0, 0) // Schwarz bei Punktlandung 0.00
  }
  doc.text(balanceText, 195, finalY, { align: 'right' })

  // --- 7. Unterschriftenbereich (weit unten platziert) ---
  doc.setTextColor(0, 0, 0)
  const sigY = 275 // Feste Position kurz vor dem unteren Seitenrand (A4 ist 297mm hoch)
  
  doc.setLineWidth(0.1)
  doc.line(15, sigY, 85, sigY)
  doc.line(125, sigY, 195, sigY)
  
  doc.setFontSize(8)
  doc.setFont('courier', 'normal')
  doc.text('Unterschrift Mitarbeiter/in', 15, sigY + 4)
  doc.text('Bestätigt (Vorgesetzte/r / HR)', 125, sigY + 4)

  // --- 8. PDF Speichern ---
  const safeName = (userName || 'Mitarbeiter').replace(/\s+/g, '_')
  const fileName = `Arbeitsnachweis_${year}_${String(data.selectedMonth + 1).padStart(2, '0')}_${safeName}.pdf`
  doc.save(fileName)
  
  return true
}