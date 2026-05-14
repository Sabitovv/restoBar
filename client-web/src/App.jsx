import { useEffect, useMemo, useState } from 'react'

const apiBase = ''

function priceText(cost) {
  return `$${(Number(cost || 0) / 100).toFixed(2)}`
}

function App() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [screen, setScreen] = useState('home')
  const [bootstrap, setBootstrap] = useState({ info: null, categories: [], popular: [], theme: {} })
  const [categoryItems, setCategoryItems] = useState([])
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [selectedItem, setSelectedItem] = useState(null)
  const [qty, setQty] = useState(1)
  const [cart, setCart] = useState([])

  const palette = bootstrap.theme?.palette || {}

  useEffect(() => {
    const fetchBootstrap = async () => {
      setLoading(true)
      setError('')
      try {
        const response = await fetch(`${apiBase}/client/bootstrap?popularLimit=8`)
        const payload = await response.json()
        if (!response.ok) throw new Error(payload.message || 'Load failed')
        setBootstrap(payload)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    fetchBootstrap()
  }, [])

  const cartTotal = useMemo(() => cart.reduce((sum, item) => sum + Number(item.variant.cost) * item.quantity, 0), [cart])

  const openCategory = async (category) => {
    setSelectedCategory(category)
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${apiBase}/menu/${category.id}`)
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.message || 'Failed to load category')
      setCategoryItems(payload)
      setScreen('category')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const openDetails = async (itemId) => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${apiBase}/menu/details/${itemId}`)
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.message || 'Failed to load details')
      setSelectedItem(payload)
      setQty(1)
      setScreen('details')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const addToCart = () => {
    if (!selectedItem?.variants?.length) return
    const variant = selectedItem.variants[0]
    const id = `${selectedItem.id}:${variant.id}`
    setCart((prev) => {
      const existing = prev.find((item) => item.id === id)
      if (existing) {
        return prev.map((item) => item.id === id ? { ...item, quantity: item.quantity + qty } : item)
      }
      return [...prev, { id, item: selectedItem, variant, quantity: qty }]
    })
    setScreen('category')
  }

  const rootStyle = {
    '--bg': palette.bg || '#fdf6ee',
    '--surface': palette.surface || '#fffaf4',
    '--text': palette.text || '#2f241b',
    '--muted': palette.muted || '#6f5f51',
    '--primary': palette.primary || '#b25a2b',
    '--accent': palette.accent || '#e29a4a',
  }

  return (
    <main className="app" style={rootStyle}>
      <header className="topbar">
        <button type="button" onClick={() => setScreen('home')}>Home</button>
        <h1>{bootstrap.info?.name || 'Cafe'}</h1>
        <button type="button" onClick={() => setScreen('cart')}>Cart ({cart.length})</button>
      </header>

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Loading...</p>}

      {!loading && screen === 'home' && (
        <section className="page">
          {bootstrap.info?.coverImage && <img className="hero" src={bootstrap.info.coverImage} alt="cover" />}
          <h2>Categories</h2>
          <div className="grid cats">
            {(bootstrap.categories || []).map((category) => (
              <button key={category.id} className="cat" style={{ background: category.backgroundColor || 'var(--surface)' }} onClick={() => openCategory(category)}>
                {category.icon ? <img src={category.icon} alt="" /> : null}
                <span>{category.name}</span>
              </button>
            ))}
          </div>

          <h2>Popular</h2>
          <div className="grid items">
            {(bootstrap.popular || []).map((item) => (
              <article className="card" key={item.id} onClick={() => openDetails(item.id)}>
                {item.image && <img src={item.image} alt={item.name} />}
                <h3>{item.name}</h3>
                <p>{item.description}</p>
              </article>
            ))}
          </div>
        </section>
      )}

      {!loading && screen === 'category' && (
        <section className="page">
          <h2>{selectedCategory?.name || 'Category'}</h2>
          <div className="grid items">
            {categoryItems.map((item) => (
              <article className="card" key={item.id} onClick={() => openDetails(item.id)}>
                {item.image && <img src={item.image} alt={item.name} />}
                <h3>{item.name}</h3>
                <p>{item.description}</p>
                <strong>{priceText(item.variants?.[0]?.cost)}</strong>
              </article>
            ))}
          </div>
        </section>
      )}

      {!loading && screen === 'details' && selectedItem && (
        <section className="page">
          {selectedItem.image && <img className="hero" src={selectedItem.image} alt={selectedItem.name} />}
          <h2>{selectedItem.name}</h2>
          <p>{selectedItem.description}</p>
          <p className="muted">{selectedItem.variants?.[0]?.weight || ''}</p>
          <div className="row">
            <button type="button" onClick={() => setQty((v) => Math.max(1, v - 1))}>-</button>
            <span>{qty}</span>
            <button type="button" onClick={() => setQty((v) => v + 1)}>+</button>
          </div>
          <button type="button" className="primary" onClick={addToCart}>Add to cart</button>
        </section>
      )}

      {!loading && screen === 'cart' && (
        <section className="page">
          <h2>Cart</h2>
          {cart.length === 0 && <p className="muted">Your cart is empty.</p>}
          {cart.map((row) => (
            <article className="cartrow" key={row.id}>
              <div>
                <strong>{row.item.name}</strong>
                <p>{row.variant.name}</p>
              </div>
              <div>{row.quantity} x {priceText(row.variant.cost)}</div>
            </article>
          ))}
          <h3>Total: {priceText(cartTotal)}</h3>
        </section>
      )}
    </main>
  )
}

export default App
