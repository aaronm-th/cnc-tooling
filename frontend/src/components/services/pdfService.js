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

  doc.setFont('courier', 'bold')
  doc.text('SOLL-MONAT:', 140, 36)
  doc.setFont('courier', 'normal')
  doc.text(`${parseFloat(monthly_soll || 0).toFixed(2)} h`, 172, 36)

  doc.setFont('courier', 'bold')
  doc.text('IST-MONAT:', 140, 41)
  doc.setFont('courier', 'normal')
  doc.text(`${parseFloat(monthly_ist || 0).toFixed(2)} h`, 172, 41)

  doc.setFont('courier', 'bold')
  doc.text('DIFFERENZ:', 140, 46)
  doc.setFont('courier', 'normal')
  const totalDiffNum = parseFloat(monthly_diff || 0)
  const totalPrefix = totalDiffNum > 0 ? '+' : ''
  doc.text(`${totalPrefix}${totalDiffNum.toFixed(2)} h`, 172, 46)

  // --- 4. Datenaufbereitung für das Tabellen-Raster ---
  const tableData = (events || []).map(day => {
    const dateObj = new Date(day.date)

    const germanDate = dateObj.toLocaleDateString('de-DE', {
      weekday: 'short',
      day: '2-digit',
      month: '2-digit'
    }).replace('.', '')

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
    ]
  })

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
      fillColor: [255, 255, 255], // Sehr dezentes Grau für den Header
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
    const opacityState = new doc.GState({ opacity: 0.10 }) // 10% Deckkraft
    doc.setGState(opacityState)

    doc.setTextColor(220, 38, 38) // Ein dezenter Rotton
    doc.setFont('helvetica', 'bold') // Helvetica skaliert bei Riesen-Schrift stabiler als Courier
    doc.setFontSize(60)

    // Absolute Platzierung auf DIN A4 (Breite 210mm, Höhe 297mm)
    // Wir starten im linken unteren Quadranten (x=35, y=190) und rotieren um 45 Grad nach rechts oben.
    // Das zieht den Text quer über das gesamte Blatt, ohne vom Koordinatensystem der Tabelle gestört zu werden.
    doc.text('VORLÄUFIG / DRAFT', 35, 190, { angle: 45 })

    // Status sofort wieder für den Rest des Dokuments zurücksetzen!
    const normalState = new doc.GState({ opacity: 1.0 })
    doc.setGState(normalState)
  }

  // --- 6. Zusammenfassung & Abschluss ---
  doc.setTextColor(0, 0, 0)
  const finalY = doc.lastAutoTable.finalY + 8

  doc.setFontSize(10)
  doc.setFont('courier', 'bold')

  // Formatierung des Gesamtsaldos (Basiert nun wasserdicht auf dem Backend-Wert)
  const finalDiffNum = parseFloat(monthly_diff || 0)
  const finalPrefix = finalDiffNum > 0 ? '+' : ''
  const balanceText = `GESAMT-SALDO MONAT: ${finalPrefix}${finalDiffNum.toFixed(2)} h`

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
    // Kleine Verzögerung, damit der PDF-Renderer im iframe wirklich fertig ist,
    // bevor der Druckdialog aufgerufen wird
    setTimeout(() => {
      iframe.contentWindow.focus()
      iframe.contentWindow.print()
    }, 300)
  }

  // Aufräumen, sobald der Druckdialog geschlossen wird
  // (Fokus kehrt zum Hauptfenster zurück, egal ob gedruckt oder abgebrochen)
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