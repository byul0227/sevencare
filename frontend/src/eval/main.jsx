import { createRoot } from 'react-dom/client'
import '../styles/tokens.css'
import './eval.css'
import EvalApp from './EvalApp.jsx'

createRoot(document.getElementById('root')).render(<EvalApp />)
