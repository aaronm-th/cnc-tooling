import { Clock, Palmtree, Stethoscope, Landmark, Sun, Hourglass } from 'lucide-vue-next'

export function useEventStyles() {
  const getEventClass = (event) => {
    // Falls ein String statt eines Objekts übergeben wurde (Fallback)
    if (typeof event === 'string') {
      return getEventClassByType(event)
    }

    // --- NEU: Wenn der Antrag noch offen (pending) ist -> Gelb/Amber färben ---
    if (event?.isRequest && event?.isPending) {
      return 'bg-amber-100 text-amber-700 border-amber-300'
    }

    // Normales Fallback auf den Event-Typen, wenn genehmigt oder regulär
    return getEventClassByType(event?.type)
  }

  // Die alte Logik ausgelagert als Hilfsfunktion für genehmigte/reguläre Typen
  const getEventClassByType = (type) => {
    const t = type?.toLowerCase()
    if (t === 'work') return 'bg-blue-100 text-blue-700 border-blue-300'
    if (t === 'vacation') return 'bg-emerald-100 text-emerald-700 border-emerald-300'
    if (t === 'sick') return 'bg-red-100 text-red-700 border-red-300'
    if (t === 'pending') return 'bg-amber-100 text-amber-700 border-amber-300'
    if (t === 'holiday') return 'bg-violet-200 text-violet-700 border-violet-300'
    return 'bg-slate-100 text-slate-700 border-slate-300'
  }

  const getStatusColor = (status) => {
    const s = status?.toLowerCase()
    
    // Mapping von "Menschlich" auf "Technisch"
    const typeMapping = {
      'anwesend': 'vacation',
      'active': 'work',
      'urlaub': 'vacation',
      'vacation': 'vacation',
      'krank': 'sick',
      'sick': 'sick',
      'pending': 'pending',
      }
    
    const type = typeMapping[s] || 'default'
    
    return getEventClass(type)
    }

  const getActiveStyles = (id) => {
    const t = id.toLowerCase()
    if (t === 'holiday' || t === 'vacation') 
      return 'bg-emerald-50 border-emerald-500 text-emerald-700 shadow-lg shadow-emerald-500/10 scale-[1.02]'
    if (t === 'sick') 
      return 'bg-red-50 border-red-500 text-red-700 shadow-lg shadow-red-500/10 scale-[1.02]'
    return 'bg-blue-50 border-blue-500 text-blue-700 shadow-lg shadow-blue-500/10 scale-[1.02]'
  }

  const getEventIcon = (type) => {
    const t = type?.toLowerCase()
    switch (t) {
      case 'work': return Clock
      case 'vacation': return Palmtree
      case 'sick': return Stethoscope
      case 'holiday': return Landmark
      case 'weekend': return Sun
      case 'pending': return Hourglass
      default: return Clock 
    }
  }

  const getIconColorClass = (type) => {
    const t = type?.toLowerCase()
    switch (t) {
      case 'work': return 'text-blue-500'
      case 'vacation': return 'text-emerald-500'
      case 'sick': return 'text-red-500'
      case 'pending': return 'text-amber-500'
      default: return 'text-slate-500'
    }
  }

  const getBadgeColorClass = (type) => {
    const t = type?.toLowerCase()
    switch (t) {
      case 'work': 
        return 'bg-blue-50 text-blue-700 border-blue-100'
      case 'vacation': 
        return 'bg-emerald-50 text-emerald-700 border-emerald-100'
      case 'sick': 
        return 'bg-red-50 text-red-700 border-red-100'
      case 'holiday':
        return 'bg-amber-50 text-amber-700 border-amber-100'
      default: 
        return 'bg-slate-50 text-slate-700 border-slate-100'
    }
  }

  const getStatusColorClass = (status) => {
    const s = status?.toLowerCase()
    switch (s) {
      case 'genehmigt':
      case 'approved':
        return 'bg-emerald-100 text-emerald-700 border-emerald-200'
      case 'abgelehnt':
      case 'rejected':
        return 'bg-red-100 text-red-700 border-red-200'
      case 'in bearbeitung':
      case 'pending':
        return 'bg-amber-100 text-amber-700 border-amber-200 shadow-sm shadow-amber-500/10'
      default:
        return 'bg-slate-100 text-slate-600 border-slate-200'
    }
  }


  return { getEventClass, getEventIcon, getIconColorClass, getActiveStyles, getStatusColorClass, getStatusColor, getBadgeColorClass }
}