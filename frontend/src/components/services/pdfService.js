import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'

// ---------------------------------------------------------------------------
// "Speichern unter" via File System Access API (nur Chromium + Secure Context)
// Fällt automatisch auf klassischen Download zurück, wenn nicht verfügbar.
// ---------------------------------------------------------------------------
export const saveWorkingHoursPDFAs = async (pdfBlob, filename) => {
  if ('showSaveFilePicker' in window) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: filename,
        types: [{
          description: 'PDF-Dokument',
          accept: { 'application/pdf': ['.pdf'] }
        }]
      })
      const writable = await handle.createWritable()
      await writable.write(pdfBlob)
      await writable.close()
      return true
    } catch (err) {
      // Nutzer hat den Dialog abgebrochen -> kein Fehler, einfach nichts tun
      if (err.name === 'AbortError') return false
      throw err
    }
  } else {
    // Fallback für Firefox/Safari bzw. unsichere Kontexte: klassischer Download
    const url = URL.createObjectURL(pdfBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
    return true
  }
}

// ---------------------------------------------------------------------------
// Reine PDF-Erzeugung: baut das jsPDF-Dokument auf und gibt es zurück.
// Wird sowohl von generateWorkingHoursPDF (Tab/Download) als auch von
// printWorkingHoursPDF (Direktdruck) genutzt, damit die Layout-Logik nur
// an einer Stelle gepflegt werden muss.
// ---------------------------------------------------------------------------
const buildWorkingHoursPDF = (data) => {
  const { monthName, year, userName, events, monthly_soll, monthly_ist, monthly_diff } = data

  // A4-Format initialisieren (Ein-Seiten-Sicherheits-Layout)
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  })

  const today = new Date().toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })

  // --- 1. Globalen Font auf Courier setzen (Schreibmaschine) ---
  doc.setFont('courier', 'normal')

  // --- 2. Header (Stempel-Stil) ---
  doc.setFontSize(16)
  doc.setFont('courier', 'bold')
  doc.setTextColor(0, 0, 0)
  doc.text('ZEITNACHWEIS', 15, 20)

  doc.setFontSize(9)
  doc.setFont('courier', 'normal')

  // Ausstellungsdatum oben rechts, auf Höhe des Titels
  const todayW = doc.getTextWidth(today)   // Breite im aktuellen Font (normal)
  doc.text(today, 195, 20, { align: 'right' })
  doc.text('erstellt am', 195 - todayW - 2, 20, { align: 'right' })

  // Trennlinie
  doc.setLineWidth(0.2)
  doc.setDrawColor(0, 0, 0)
  doc.line(15, 24, 195, 24)

  // --- 3. Info-Block: eine Zeile, links Mitarbeiter, rechts Zeitraum ---
  doc.setFontSize(9)

  doc.setFont('courier', 'bold')
  doc.text('MITARBEITER:', 15, 34)
  doc.setFont('courier', 'normal')
  doc.text((userName || 'Mitarbeiter').toUpperCase(), 48, 34)

  const periodText = `${(monthName || '').toUpperCase()} ${year}`
  const periodW = doc.getTextWidth(periodText)
  doc.text(periodText, 195, 34, { align: 'right' })
  doc.setFont('courier', 'bold')
  doc.text('ZEITRAUM:', 195 - periodW - 2, 34, { align: 'right' })

  

  // --- 4. Datenaufbereitung für das Tabellen-Raster ---
  const tableData = (events || []).map(day => {
    const dateObj = new Date(day.date)

    const germanDate = dateObj.toLocaleDateString('de-DE', {
      weekday: 'short',
      day: '2-digit',
      month: '2-digit'
    }).replace('.', '')

    const dayDiffNum = parseFloat(day.diff || 0)
    let diffStr = '0.00 h'
    if (dayDiffNum > 0) {
      diffStr = `+${dayDiffNum.toFixed(2)} h`
    } else if (dayDiffNum < 0) {
      diffStr = `${dayDiffNum.toFixed(2)} h`
    }

    return [
      germanDate,
      day.day_type_display ? day.day_type_display.toUpperCase() : 'ARBEITSTAG',
      day.soll_hours != null ? `${parseFloat(day.soll_hours).toFixed(2)} h` : '0.00 h',     
      day.actual_hours != null ? `${parseFloat(day.actual_hours).toFixed(2)} h` : '0.00 h', 
      diffStr,
      day.session_details || '-'
    ]
  })

  // --- 5. Tabelle im echten Schreibmaschinen-Gitterraster ---
  autoTable(doc, {
    startY: 44,
    margin: { left: 15, right: 15 },
    head: [['DATUM', 'STATUS / TYP', 'SOLL', 'IST', 'SALDO', 'DETAILS']],
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
      fillColor: [255, 255, 255], // Sehr dezentes Grau für den Header
      textColor: [0, 0, 0],
      fontStyle: 'bold',
      lineWidth: 0.2,
      halign: 'left'
    },
    columnStyles: {
      0: { cellWidth: 20 },  // DATUM
      1: { cellWidth: 26 },  // STATUS / TYP
      2: { cellWidth: 16, halign: 'right' }, // SOLL
      3: { cellWidth: 16, halign: 'right' }, // IST
      4: { cellWidth: 18, halign: 'right' }, // SALDO
      5: { cellWidth: 'auto' } // ZEITRÄUME
    },
    didParseCell: function (data) {
      if (data.section === 'body') {
        const rowIndex = data.row.index
        const rawDay = events[rowIndex]

        if (rawDay) {
          // Wochenenden & Feiertage leicht ausgrauen
          if (['weekend', 'holiday'].includes(rawDay.day_type)) {
            data.cell.styles.textColor = [0, 0, 0]
          }

          // Urlaub & Krankheit fett hervorheben
          if (['vacation', 'leave', 'sick'].includes(rawDay.day_type)) {
            data.cell.styles.fontStyle = 'bold'
          }
        }
      }
    }
  })

  // --- Wasserzeichen absolut über die ganze Seite (ohne Align-Bug) ---
  if (!data.is_locked) {
    const opacityState = new doc.GState({ opacity: 0.15 })
    doc.setGState(opacityState)

    doc.setTextColor(220, 38, 38) // Ein dezenter Rotton
    doc.setFont('helvetica', 'bold') // Helvetica skaliert bei Riesen-Schrift stabiler als Courier
    doc.setFontSize(60)

    // Absolute Platzierung auf DIN A4 (Breite 210mm, Höhe 297mm)
    doc.text('VORLÄUFIG / DRAFT', 35, 210, { angle: 45 })

    // Status sofort wieder für den Rest des Dokuments zurücksetzen!
    const normalState = new doc.GState({ opacity: 1.0 })
    doc.setGState(normalState)
  }

   // --- 6. Summenblock unter der Tabelle ---
  doc.setTextColor(0, 0, 0)

  const sumHours = (types) =>
    (events || [])
      .filter(e => types.includes(e.day_type))
      .reduce((s, e) => s + parseFloat(e.actual_hours || 0), 0)

  const ist = parseFloat(monthly_ist || 0)
  const soll = parseFloat(monthly_soll || 0)
  const diff = parseFloat(monthly_diff || 0)
  const urlaub = sumHours(['vacation', 'leave'])
  const krank = sumHours(['sick'])
  const arbeit = ist - urlaub - krank

  const fmt = (n) => `${n.toFixed(2)} h`
  const summaryRows = [
    ['SOLL', fmt(soll)],
    ['IST', fmt(ist)],
    ['  davon Arbeit', fmt(arbeit)],
    ['  davon Urlaub', fmt(urlaub)],
    ['  davon Krankheit', fmt(krank)],
    ['SALDO', `${diff > 0 ? '+' : ''}${fmt(diff)}`]
  ]

  let summaryY = doc.lastAutoTable.finalY + 6
  const summaryHeight = summaryRows.length * 5.5
  if (summaryY + summaryHeight > 285) {
    doc.addPage()
    summaryY = 20
  }

    // Breite der DETAILS-Spalte (letzte Spalte) der Haupttabelle übernehmen
  const pageW = doc.internal.pageSize.getWidth()
  const detailsW = doc.lastAutoTable.columns[5].width
  const valueW = 30

  autoTable(doc, {
    startY: summaryY,
    margin: { left: pageW - 15 - detailsW, right: 15 },
    tableWidth: detailsW,
    body: summaryRows,
    theme: 'grid',
    styles: {
      font: 'courier',
      fontSize: 8,
      cellPadding: 1.2,
      textColor: [0, 0, 0],
      lineColor: [0, 0, 0],
      lineWidth: 0.1
    },
    columnStyles: {
      0: { cellWidth: detailsW - valueW },
      1: { cellWidth: valueW, halign: 'right' }
    },
    didParseCell: (d) => {
      if ([0, 1, 5].includes(d.row.index)) d.cell.styles.fontStyle = 'bold'
    }
  })

  return doc
}

// ---------------------------------------------------------------------------
// Direktdruck: unabhängig vom Tab-Öffnen unten. Nutzt ein unsichtbares
// iframe im aktuellen Fenster, keine Navigation, kein Download-Trigger ->
// funktioniert auch unter HTTP, ohne Secure Context.
// ---------------------------------------------------------------------------
const printPdfBlob = (pdfBlob) => {
  const blobUrl = URL.createObjectURL(pdfBlob)
  const iframe = document.createElement('iframe')
  iframe.style.position = 'fixed'
  iframe.style.right = '0'
  iframe.style.bottom = '0'
  iframe.style.width = '0'
  iframe.style.height = '0'
  iframe.style.border = '0'
  iframe.src = blobUrl

  const cleanup = () => {
    if (iframe.parentNode) document.body.removeChild(iframe)
    URL.revokeObjectURL(blobUrl)
  }

  iframe.onload = () => {
    setTimeout(() => {
      iframe.contentWindow.focus()
      iframe.contentWindow.print()
    }, 300)
  }

  window.addEventListener('focus', cleanup, { once: true })

  document.body.appendChild(iframe)
}

export const printWorkingHoursPDF = (data) => {
  const doc = buildWorkingHoursPDF(data)
  const pdfBlob = doc.output('blob')
  printPdfBlob(pdfBlob)
}

// ---------------------------------------------------------------------------
// Generiert den Report und öffnet ihn direkt im übergebenen Tab-Fenster
// (nativer Browser-PDF-Viewer, keine eigene Toolbar) oder lädt ihn,
// falls kein Fenster übergeben wurde, klassisch herunter.
// ---------------------------------------------------------------------------
export const generateWorkingHoursPDF = async (data, targetWindow = null) => {
  const doc = buildWorkingHoursPDF(data)
  const { userName, monthName, year } = data

  const employeeName = (userName).replace(/\s+/g, '_')
  const suffix = data.is_locked ? '' : '_draft'
  const filename = `Zeitnachweis_${year}_${monthName}_${employeeName}${suffix}.pdf`

  // Titel in den PDF-Metadaten setzen, damit der Tab im Browser sinnvoll benannt ist
  doc.setProperties({ title: filename })

  if (targetWindow && !targetWindow.closed) {
    const pdfBlob = doc.output('blob')
    const blobUrl = URL.createObjectURL(pdfBlob)
    targetWindow.location.href = blobUrl
  } else {
    const pdfBlob = doc.output('blob')
    await saveWorkingHoursPDFAs(pdfBlob, filename)
  }

  return true
}