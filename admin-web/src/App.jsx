import { useEffect, useMemo, useState } from 'react'
import './App.css'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
const MAX_IMAGE_FILE_BYTES = 3 * 1024 * 1024
const MAX_IMAGE_EDGE = 1600

function App() {
  const [principal, setPrincipal] = useState(() => {
    const saved = localStorage.getItem('adminPrincipal')
    return saved ? JSON.parse(saved) : null
  })
  const [status, setStatus] = useState('idle')
  const [message, setMessage] = useState('Open this panel from Telegram bot with Open Admin button.')
  const [tab, setTab] = useState('restaurants')
  const [loading, setLoading] = useState(false)

  const [restaurants, setRestaurants] = useState([])
  const [staffItems, setStaffItems] = useState([])
  const [categories, setCategories] = useState([])
  const [menuItems, setMenuItems] = useState([])
  const [restaurantProfile, setRestaurantProfile] = useState({
    name: '',
    about: '',
    previewImage: '',
    workingHours: {
      mon: '', tue: '', wed: '', thu: '', fri: '', sat: '', sun: '',
    },
  })

  const [selectedRestaurantId, setSelectedRestaurantId] = useState('')
  const [selectedCategoryId, setSelectedCategoryId] = useState('')
  const [categorySearch, setCategorySearch] = useState('')
  const [dishSearch, setDishSearch] = useState('')
  const [dishSort, setDishSort] = useState('name_asc')

  const [restaurantForm, setRestaurantForm] = useState({ name: '', slug: '' })
  const [inviteForm, setInviteForm] = useState({ username: '', role: 'admin', restaurantId: '' })
  const [categoryForm, setCategoryForm] = useState({ name: '', image: '', isActive: true })
  const [itemForm, setItemForm] = useState({
    name: '',
    categoryId: '',
    oldPriceMinor: '',
    newPriceMinor: '500',
    description: '',
    recipeText: '',
    image: '',
    isAvailableNow: true,
  })
  const [editingItem, setEditingItem] = useState(null)
  const [editingCategory, setEditingCategory] = useState(null)
  const [draggingCategoryId, setDraggingCategoryId] = useState('')
  const [creatingCategory, setCreatingCategory] = useState(false)
  const [creatingDish, setCreatingDish] = useState(false)
  const [editItemForm, setEditItemForm] = useState({
    id: '',
    name: '',
    categoryId: '',
    oldPriceMinor: '',
    newPriceMinor: '0',
    description: '',
    recipeText: '',
    image: '',
    isAvailableNow: true,
  })
  const [deleteCandidate, setDeleteCandidate] = useState(null)
  const [editCategoryForm, setEditCategoryForm] = useState({ id: '', name: '', image: '', isActive: true })

  const isSuper = principal?.role === 'super_admin'
  const isAdmin = principal?.role === 'admin'
  const isManager = principal?.role === 'manager'

  const availableTabs = useMemo(() => {
    if (isSuper) return ['restaurants', 'staff']
    if (isAdmin) return ['restaurant', 'categories', 'items', 'staff']
    if (isManager) return ['restaurant', 'categories', 'items']
    return []
  }, [isSuper, isAdmin, isManager])

  const filteredCategories = useMemo(() => {
    const q = categorySearch.trim().toLowerCase()
    if (!q) return categories
    return categories.filter((item) => (item.name || '').toLowerCase().includes(q))
  }, [categories, categorySearch])

  const filteredDishes = useMemo(() => {
    const q = dishSearch.trim().toLowerCase()
    const list = q ? menuItems.filter((item) => (item.name || '').toLowerCase().includes(q)) : [...menuItems]
    return list.sort((a, b) => {
      const ap = Number(a.variants?.[0]?.priceMinor || 0)
      const bp = Number(b.variants?.[0]?.priceMinor || 0)
      if (dishSort === 'name_desc') return (b.name || '').localeCompare(a.name || '')
      if (dishSort === 'price_asc') return ap - bp
      if (dishSort === 'price_desc') return bp - ap
      return (a.name || '').localeCompare(b.name || '')
    })
  }, [menuItems, dishSearch, dishSort])

  const categoryNameById = useMemo(() => {
    const map = new Map()
    categories.forEach((item) => map.set(item.id, item.name || item.id))
    return map
  }, [categories])

  const token = () => localStorage.getItem('adminAccessToken')

  const parseRecipe = (recipeText) => recipeText
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

  const splitPrices = (oldValue, newValue) => {
    const hasOld = String(oldValue || '').trim() !== ''
    const hasNew = String(newValue || '').trim() !== ''
    if (!hasOld && !hasNew) throw new Error('Add old price, new price, or both.')

    const oldPrice = hasOld ? Number(oldValue) : null
    const newPrice = hasNew ? Number(newValue) : null
    if (oldPrice !== null && !(oldPrice > 0)) throw new Error('Old price must be > 0.')
    if (newPrice !== null && !(newPrice > 0)) throw new Error('New price must be > 0.')

    if (oldPrice !== null && newPrice !== null) {
      if (newPrice > oldPrice) throw new Error('New price cannot be greater than old price.')
      if (newPrice === oldPrice) return { priceMinor: oldPrice, discountMinor: 0, discountIsActive: false }
      return { priceMinor: oldPrice, discountMinor: oldPrice - newPrice, discountIsActive: true }
    }

    const priceMinor = oldPrice ?? newPrice
    return { priceMinor, discountMinor: 0, discountIsActive: false }
  }

  const api = async (path, options = {}) => {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token()}`,
        ...(options.headers || {}),
      },
    })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(payload.message || 'Request failed')
    }
    return payload
  }

  const toast = (kind, text) => {
    setStatus(kind)
    setMessage(text)
  }

  const fileToDataUrl = (file) => new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('Could not read selected file.'))
    reader.readAsDataURL(file)
  })

  const loadImageFromDataUrl = (dataUrl) => new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('Could not load image.'))
    image.src = dataUrl
  })

  const compressImageDataUrl = async (dataUrl) => {
    const image = await loadImageFromDataUrl(dataUrl)
    const ratio = Math.min(1, MAX_IMAGE_EDGE / Math.max(image.width, image.height))
    const targetWidth = Math.max(1, Math.round(image.width * ratio))
    const targetHeight = Math.max(1, Math.round(image.height * ratio))
    const canvas = document.createElement('canvas')
    canvas.width = targetWidth
    canvas.height = targetHeight
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Could not prepare image compressor.')
    context.drawImage(image, 0, 0, targetWidth, targetHeight)

    let quality = 0.86
    let output = canvas.toDataURL('image/jpeg', quality)
    while (output.length > 4_500_000 && quality > 0.45) {
      quality -= 0.08
      output = canvas.toDataURL('image/jpeg', quality)
    }
    if (output.length > 4_500_000) {
      throw new Error('Image is still too large after compression. Choose a smaller image.')
    }
    return output
  }

  useEffect(() => {
    const webApp = window.Telegram?.WebApp
    webApp?.ready()
    const initData = webApp?.initData
    if (!initData) {
      setStatus('error')
      setMessage('Open this panel from Telegram bot with Open Admin button.')
      return
    }

    const authorize = async () => {
      setLoading(true)
      try {
        const response = await fetch(`${apiBaseUrl}/admin/auth/webapp`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ initData }),
        })
        const payload = await response.json()
        if (!response.ok) throw new Error(payload.message || 'Authorization failed')
        localStorage.setItem('adminAccessToken', payload.accessToken)
        localStorage.setItem('adminPrincipal', JSON.stringify(payload.principal))
        setPrincipal(payload.principal)
        toast('success', 'Access granted.')
      } catch (error) {
        toast('error', error.message)
      } finally {
        setLoading(false)
      }
    }

    authorize()
  }, [])

  useEffect(() => {
    if (!principal || !availableTabs.length) return
    if (!availableTabs.includes(tab)) setTab(availableTabs[0])
  }, [principal, availableTabs, tab])

  useEffect(() => {
    if (!principal) return
    const loadBase = async () => {
      try {
        const data = await api('/admin/restaurants')
        setRestaurants(data.items || [])
        const firstId = data.items?.[0]?.id || ''
        if (!selectedRestaurantId && firstId) {
          setSelectedRestaurantId(firstId)
          setInviteForm((state) => ({ ...state, restaurantId: firstId }))
        }
      } catch (error) {
        toast('error', error.message)
      }
    }
    loadBase()
  }, [principal])

  const loadStaff = async () => {
    if (!principal) return
    const restaurantId = isSuper ? selectedRestaurantId : principal.restaurantId
    if (!restaurantId) return setStaffItems([])
    const data = await api(`/admin/staff?restaurantId=${restaurantId}`)
    setStaffItems(data.items || [])
  }

  const loadCategories = async () => {
    if (!principal || isSuper) return setCategories([])
    const data = await api('/admin/menu/categories')
    setCategories(data.items || [])
    if (!selectedCategoryId && data.items?.length) {
      setSelectedCategoryId(data.items[0].id)
      setItemForm((state) => ({ ...state, categoryId: data.items[0].id }))
    }
  }

  const loadRestaurantProfile = async () => {
    if (!principal || isSuper) return
    const data = await api('/admin/restaurant/profile')
    setRestaurantProfile({
      name: data.name || '',
      about: data.about || '',
      previewImage: data.previewImage || '',
      workingHours: {
        mon: data.workingHours?.mon || '',
        tue: data.workingHours?.tue || '',
        wed: data.workingHours?.wed || '',
        thu: data.workingHours?.thu || '',
        fri: data.workingHours?.fri || '',
        sat: data.workingHours?.sat || '',
        sun: data.workingHours?.sun || '',
      },
    })
  }

  const loadMenuItems = async () => {
    if (!principal || isSuper) return setMenuItems([])
    const query = selectedCategoryId ? `?categoryId=${selectedCategoryId}` : ''
    const data = await api(`/admin/menu/items${query}`)
    setMenuItems(data.items || [])
  }

  useEffect(() => {
    if (!principal) return
    const loadTabData = async () => {
      setLoading(true)
      try {
        if (tab === 'staff') await loadStaff()
        if (tab === 'restaurant') await loadRestaurantProfile()
        if (tab === 'categories') await loadCategories()
        if (tab === 'items') {
          await loadCategories()
          await loadMenuItems()
        }
      } catch (error) {
        toast('error', error.message)
      } finally {
        setLoading(false)
      }
    }
    loadTabData()
  }, [tab, principal, selectedRestaurantId, selectedCategoryId])

  const onCreateRestaurant = async (event) => {
    event.preventDefault()
    setLoading(true)
    try {
      await api('/admin/restaurants', { method: 'POST', body: JSON.stringify(restaurantForm) })
      setRestaurantForm({ name: '', slug: '' })
      toast('success', 'Restaurant created.')
      const data = await api('/admin/restaurants')
      setRestaurants(data.items || [])
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const onDeleteRestaurant = async (id) => {
    if (!window.confirm('Delete restaurant? It will become inactive.')) return
    setLoading(true)
    try {
      await api(`/admin/restaurants/${id}`, { method: 'DELETE' })
      toast('success', 'Restaurant set inactive.')
      const data = await api('/admin/restaurants')
      setRestaurants(data.items || [])
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const onInvite = async (event) => {
    event.preventDefault()
    setLoading(true)
    try {
      const payload = {
        username: inviteForm.username,
        role: inviteForm.role,
      }
      if (isSuper) payload.restaurantId = inviteForm.restaurantId
      await api('/admin/staff/invite', { method: 'POST', body: JSON.stringify(payload) })
      setInviteForm((state) => ({ ...state, username: '' }))
      toast('success', 'Invitation created.')
      await loadStaff()
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const onRevokeStaff = async (id) => {
    if (!window.confirm('Revoke access?')) return
    setLoading(true)
    try {
      await api(`/admin/staff/${id}`, { method: 'DELETE' })
      toast('success', 'Access revoked.')
      await loadStaff()
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const onCreateCategory = async (event) => {
    event.preventDefault()
    setLoading(true)
    try {
      await api('/admin/menu/categories', { method: 'POST', body: JSON.stringify(categoryForm) })
      setCategoryForm({ name: '', image: '', isActive: true })
      toast('success', 'Category created.')
      setCreatingCategory(false)
      await loadCategories()
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const openEditCategory = (category) => {
    setEditingCategory(category)
    setEditCategoryForm({
      id: category.id,
      name: category.name || '',
      image: category.image || '',
      isActive: Boolean(category.isActive),
    })
  }

  const closeEditCategory = () => {
    setEditingCategory(null)
  }

  const onSaveEditCategory = async (event) => {
    event.preventDefault()
    setLoading(true)
    try {
      if (!editCategoryForm.name.trim()) throw new Error('Category name is required.')
      await api(`/admin/menu/categories/${editCategoryForm.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ name: editCategoryForm.name, image: editCategoryForm.image, isActive: editCategoryForm.isActive }),
      })
      toast('success', 'Category updated.')
      closeEditCategory()
      await loadCategories()
      await loadMenuItems()
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const onPickCreateCategoryImage = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (file.size > MAX_IMAGE_FILE_BYTES) {
      toast('error', 'Image is too large. Max size is 3 MB.')
      event.target.value = ''
      return
    }
    try {
      const dataUrl = await fileToDataUrl(file)
      const compressed = await compressImageDataUrl(dataUrl)
      setCategoryForm((state) => ({ ...state, image: compressed }))
      toast('success', 'Category image selected and compressed.')
    } catch (error) {
      toast('error', error.message)
    }
  }

  const onPickEditCategoryImage = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (file.size > MAX_IMAGE_FILE_BYTES) {
      toast('error', 'Image is too large. Max size is 3 MB.')
      event.target.value = ''
      return
    }
    try {
      const dataUrl = await fileToDataUrl(file)
      const compressed = await compressImageDataUrl(dataUrl)
      setEditCategoryForm((state) => ({ ...state, image: compressed }))
      toast('success', 'Category image selected and compressed.')
    } catch (error) {
      toast('error', error.message)
    }
  }

  const onReorderCategories = async (fromId, toId) => {
    if (!fromId || !toId || fromId === toId) return
    const fromIndex = categories.findIndex((item) => item.id === fromId)
    const toIndex = categories.findIndex((item) => item.id === toId)
    if (fromIndex < 0 || toIndex < 0) return

    const next = [...categories]
    const [moved] = next.splice(fromIndex, 1)
    next.splice(toIndex, 0, moved)
    setCategories(next)

    setLoading(true)
    try {
      await api('/admin/menu/categories/reorder', {
        method: 'PATCH',
        body: JSON.stringify({ ids: next.map((item) => item.id) }),
      })
      toast('success', 'Categories order saved.')
    } catch (error) {
      toast('error', error.message)
      await loadCategories()
    } finally {
      setLoading(false)
    }
  }

  const onCreateItem = async (event) => {
    event.preventDefault()
    setLoading(true)
    try {
      const priceData = splitPrices(itemForm.oldPriceMinor, itemForm.newPriceMinor)
      if (!itemForm.name.trim()) throw new Error('Dish name is required.')
      if (!itemForm.categoryId) throw new Error('Category is required.')

      await api('/admin/menu/items', {
        method: 'POST',
        body: JSON.stringify({
          name: itemForm.name,
          categoryId: itemForm.categoryId,
          description: itemForm.description,
          recipe: parseRecipe(itemForm.recipeText),
          image: itemForm.image,
          discountMinor: priceData.discountMinor,
          discountIsActive: priceData.discountIsActive,
          isAvailableNow: itemForm.isAvailableNow,
          variants: [{ name: 'default', priceMinor: priceData.priceMinor, currency: 'USD' }],
        }),
      })
      setItemForm((state) => ({ ...state, name: '', description: '', recipeText: '', image: '', oldPriceMinor: '', newPriceMinor: '500' }))
      toast('success', 'Dish created.')
      setCreatingDish(false)
      await loadMenuItems()
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const onPickCreateImage = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (file.size > MAX_IMAGE_FILE_BYTES) {
      toast('error', 'Image is too large. Max size is 3 MB.')
      event.target.value = ''
      return
    }
    try {
      const dataUrl = await fileToDataUrl(file)
      const compressed = await compressImageDataUrl(dataUrl)
      setItemForm((state) => ({ ...state, image: compressed }))
      toast('success', 'Image selected and compressed.')
    } catch (error) {
      toast('error', error.message)
    }
  }

  const onToggleAvailability = async (item) => {
    setLoading(true)
    try {
      await api(`/admin/menu/items/${item.id}/availability`, {
        method: 'PATCH',
        body: JSON.stringify({ isAvailableNow: !item.isAvailableNow }),
      })
      toast('success', 'Availability updated.')
      await loadMenuItems()
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const onDeleteItem = async (item) => {
    setDeleteCandidate(item)
  }

  const onConfirmDeleteItem = async () => {
    if (!deleteCandidate) return
    setLoading(true)
    try {
      await api(`/admin/menu/items/${deleteCandidate.id}`, { method: 'DELETE' })
      toast('success', 'Dish deleted.')
      setDeleteCandidate(null)
      await loadMenuItems()
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const onDuplicateItem = async (item) => {
    setLoading(true)
    try {
      await api('/admin/menu/items', {
        method: 'POST',
        body: JSON.stringify({
          name: `${item.name} Copy`,
          categoryId: item.categoryId,
          description: item.description || '',
          recipe: item.recipe || '',
          image: item.image || '',
          discountMinor: Number(item.discountMinor || 0),
          discountIsActive: Boolean(item.discountIsActive),
          isAvailableNow: Boolean(item.isAvailableNow),
          variants: [{
            name: item.variants?.[0]?.name || 'default',
            priceMinor: Number(item.variants?.[0]?.priceMinor || 0),
            currency: item.variants?.[0]?.currency || 'USD',
          }],
        }),
      })
      toast('success', 'Dish duplicated.')
      await loadMenuItems()
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const openEditItem = (item) => {
    const basePrice = Number(item.variants?.[0]?.priceMinor || 0)
    const discount = Number(item.discountMinor || 0)
    const effectivePrice = discount > 0 ? Math.max(basePrice - discount, 0) : basePrice
    setEditingItem(item)
    setEditItemForm({
      id: item.id,
      name: item.name || '',
      categoryId: item.categoryId || '',
      oldPriceMinor: discount > 0 ? String(basePrice) : '',
      newPriceMinor: String(effectivePrice || 0),
      description: item.description || '',
      recipeText: Array.isArray(item.recipe) ? item.recipe.join('\n') : (item.recipe || ''),
      image: item.image || '',
      isAvailableNow: Boolean(item.isAvailableNow),
    })
  }

  const closeEditItem = () => {
    setEditingItem(null)
  }

  const onSaveEditItem = async (event) => {
    event.preventDefault()
    setLoading(true)
    try {
      const priceData = splitPrices(editItemForm.oldPriceMinor, editItemForm.newPriceMinor)
      if (!editItemForm.name.trim()) throw new Error('Dish name is required.')
      if (!editItemForm.categoryId) throw new Error('Category is required.')

      await api(`/admin/menu/items/${editItemForm.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          name: editItemForm.name,
          categoryId: editItemForm.categoryId,
          discountMinor: priceData.discountMinor,
          discountIsActive: priceData.discountIsActive,
          description: editItemForm.description,
          recipe: parseRecipe(editItemForm.recipeText),
          image: editItemForm.image,
          isAvailableNow: editItemForm.isAvailableNow,
          variants: [{ name: 'default', priceMinor: priceData.priceMinor, currency: 'USD' }],
        }),
      })
      toast('success', 'Dish updated.')
      closeEditItem()
      await loadMenuItems()
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const onPickEditImage = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (file.size > MAX_IMAGE_FILE_BYTES) {
      toast('error', 'Image is too large. Max size is 3 MB.')
      event.target.value = ''
      return
    }
    try {
      const dataUrl = await fileToDataUrl(file)
      const compressed = await compressImageDataUrl(dataUrl)
      setEditItemForm((state) => ({ ...state, image: compressed }))
      toast('success', 'Image selected and compressed.')
    } catch (error) {
      toast('error', error.message)
    }
  }

  const onPickRestaurantPreview = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (file.size > MAX_IMAGE_FILE_BYTES) {
      toast('error', 'Image is too large. Max size is 3 MB.')
      event.target.value = ''
      return
    }
    try {
      const dataUrl = await fileToDataUrl(file)
      const compressed = await compressImageDataUrl(dataUrl)
      setRestaurantProfile((state) => ({ ...state, previewImage: compressed }))
      toast('success', 'Preview image selected and compressed.')
    } catch (error) {
      toast('error', error.message)
    }
  }

  const onSaveRestaurantProfile = async (event) => {
    event.preventDefault()
    setLoading(true)
    try {
      await api('/admin/restaurant/profile', {
        method: 'PATCH',
        body: JSON.stringify(restaurantProfile),
      })
      toast('success', 'Restaurant profile updated.')
      await loadRestaurantProfile()
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const renderRestaurants = () => (
    <section className="panel">
      <h2>Restaurants</h2>
      <form className="invite" onSubmit={onCreateRestaurant}>
        <input value={restaurantForm.name} onChange={(e) => setRestaurantForm((s) => ({ ...s, name: e.target.value }))} placeholder="Restaurant name" required />
        <input value={restaurantForm.slug} onChange={(e) => setRestaurantForm((s) => ({ ...s, slug: e.target.value }))} placeholder="slug" required />
        <button disabled={loading} type="submit">Add restaurant</button>
      </form>
      <div className="staff-list">
        {restaurants.length === 0 && <article><strong>Empty</strong><span>No restaurants yet.</span></article>}
        {restaurants.map((item) => (
          <article key={item.id}>
            <strong>{item.name}</strong>
            <span>{item.slug}</span>
            <span>{item.isActive ? 'active' : 'inactive'}</span>
            <div className="actions"><button disabled={loading} type="button" onClick={() => onDeleteRestaurant(item.id)}>Delete</button></div>
          </article>
        ))}
      </div>
    </section>
  )

  const renderStaff = () => (
    <section className="panel">
      <h2>Staff</h2>
      {isSuper && (
        <div className="invite">
          <select value={selectedRestaurantId} onChange={(e) => { setSelectedRestaurantId(e.target.value); setInviteForm((s) => ({ ...s, restaurantId: e.target.value })) }}>
            {restaurants.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <span />
          <span />
        </div>
      )}
      <form className="invite" onSubmit={onInvite}>
        <input value={inviteForm.username} onChange={(e) => setInviteForm((s) => ({ ...s, username: e.target.value }))} placeholder="Telegram username" required />
        <select value={inviteForm.role} onChange={(e) => setInviteForm((s) => ({ ...s, role: e.target.value }))}>
          {isSuper ? <option value="admin">admin</option> : <option value="manager">manager</option>}
        </select>
        {isSuper ? (
          <select value={inviteForm.restaurantId} onChange={(e) => setInviteForm((s) => ({ ...s, restaurantId: e.target.value }))}>
            {restaurants.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        ) : <span />}
        <button disabled={loading} type="submit">Invite</button>
      </form>
      <div className="staff-list">
        {staffItems.length === 0 && <article><strong>Empty</strong><span>No staff in selected restaurant.</span></article>}
        {staffItems.map((item) => (
          <article key={item.id}>
            <strong>@{item.username || 'unknown'}</strong>
            <span>{item.role}</span>
            <span>{item.status}</span>
            <div className="actions"><button disabled={loading} type="button" onClick={() => onRevokeStaff(item.id)}>Revoke</button></div>
          </article>
        ))}
      </div>
    </section>
  )

  const renderCategories = () => (
    <section className="panel">
      <div className="section-head">
        <h2>Categories</h2>
        <button disabled={loading} type="button" onClick={() => setCreatingCategory(true)}>Add category</button>
      </div>
      <div className="category-toolbar">
        <input
          value={categorySearch}
          onChange={(e) => setCategorySearch(e.target.value)}
          placeholder="Search categories"
        />
        <span className="category-count">{filteredCategories.length} found</span>
      </div>
      <div className="category-grid">
        {filteredCategories.length === 0 && <article className="category-card"><strong>Empty</strong><span>No categories found.</span></article>}
        {filteredCategories.map((item) => (
          <article
            className={`category-card ${draggingCategoryId === item.id ? 'dragging' : ''}`}
            key={item.id}
            draggable
            onDragStart={() => setDraggingCategoryId(item.id)}
            onDragEnd={() => setDraggingCategoryId('')}
            onDragOver={(event) => event.preventDefault()}
            onDrop={() => {
              onReorderCategories(draggingCategoryId, item.id)
              setDraggingCategoryId('')
            }}
          >
            {item.image && <img className="category-thumb" src={item.image} alt={`${item.name} category`} />}
            <div className="category-card-head">
              <strong>{item.name}</strong>
              <span className={`status-pill ${item.isActive ? 'on' : 'off'}`}>{item.isActive ? 'active' : 'inactive'}</span>
            </div>
            <span className="category-meta">{item.itemsCount} dishes</span>
            <div className="actions">
              <button disabled={loading} type="button" onClick={() => openEditCategory(item)}>Edit</button>
            </div>
          </article>
        ))}
      </div>

      {editingCategory && (
        <div className="modal-backdrop" onClick={closeEditCategory}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <h3>Edit Category</h3>
            <form className="invite" onSubmit={onSaveEditCategory}>
              <input value={editCategoryForm.name} onChange={(e) => setEditCategoryForm((s) => ({ ...s, name: e.target.value }))} placeholder="Category name" required />
              <input value={editCategoryForm.image} onChange={(e) => setEditCategoryForm((s) => ({ ...s, image: e.target.value }))} placeholder="Category image URL" />
              <input type="file" accept="image/*" onChange={onPickEditCategoryImage} />
              {editCategoryForm.image && <img className="image-preview" src={editCategoryForm.image} alt="Category preview" />}
              <select value={String(editCategoryForm.isActive)} onChange={(e) => setEditCategoryForm((s) => ({ ...s, isActive: e.target.value === 'true' }))}>
                <option value="true">active</option>
                <option value="false">inactive</option>
              </select>
              <button disabled={loading} type="submit">Save</button>
            </form>
            <button className="close-btn" type="button" onClick={closeEditCategory}>Close</button>
          </div>
        </div>
      )}

      {creatingCategory && (
        <div className="modal-backdrop" onClick={() => setCreatingCategory(false)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <h3>Add Category</h3>
            <form className="invite" onSubmit={onCreateCategory}>
              <input value={categoryForm.name} onChange={(e) => setCategoryForm((s) => ({ ...s, name: e.target.value }))} placeholder="Category name" required />
              <input value={categoryForm.image} onChange={(e) => setCategoryForm((s) => ({ ...s, image: e.target.value }))} placeholder="Category image URL" />
              <input type="file" accept="image/*" onChange={onPickCreateCategoryImage} />
              {categoryForm.image && <img className="image-preview" src={categoryForm.image} alt="Category preview" />}
              <select value={String(categoryForm.isActive)} onChange={(e) => setCategoryForm((s) => ({ ...s, isActive: e.target.value === 'true' }))}>
                <option value="true">active</option>
                <option value="false">inactive</option>
              </select>
              <button disabled={loading} type="submit">Create</button>
            </form>
            <button className="close-btn" type="button" onClick={() => setCreatingCategory(false)}>Close</button>
          </div>
        </div>
      )}
    </section>
  )

  const renderRestaurantProfile = () => (
    <section className="panel">
      <div className="section-head"><h2>Restaurant Info</h2></div>
      <form className="invite" onSubmit={onSaveRestaurantProfile}>
        <input value={restaurantProfile.name} onChange={(e) => setRestaurantProfile((s) => ({ ...s, name: e.target.value }))} placeholder="Restaurant name" required />
        <input value={restaurantProfile.previewImage} onChange={(e) => setRestaurantProfile((s) => ({ ...s, previewImage: e.target.value }))} placeholder="Preview image URL" />
        <input type="file" accept="image/*" onChange={onPickRestaurantPreview} />
        {restaurantProfile.previewImage && <img className="image-preview" src={restaurantProfile.previewImage} alt="Restaurant preview" />}
        <textarea value={restaurantProfile.about} onChange={(e) => setRestaurantProfile((s) => ({ ...s, about: e.target.value }))} placeholder="About restaurant" rows={3} />
        <input value={restaurantProfile.workingHours.mon} onChange={(e) => setRestaurantProfile((s) => ({ ...s, workingHours: { ...s.workingHours, mon: e.target.value } }))} placeholder="Mon 09:00-22:00" />
        <input value={restaurantProfile.workingHours.tue} onChange={(e) => setRestaurantProfile((s) => ({ ...s, workingHours: { ...s.workingHours, tue: e.target.value } }))} placeholder="Tue 09:00-22:00" />
        <input value={restaurantProfile.workingHours.wed} onChange={(e) => setRestaurantProfile((s) => ({ ...s, workingHours: { ...s.workingHours, wed: e.target.value } }))} placeholder="Wed 09:00-22:00" />
        <input value={restaurantProfile.workingHours.thu} onChange={(e) => setRestaurantProfile((s) => ({ ...s, workingHours: { ...s.workingHours, thu: e.target.value } }))} placeholder="Thu 09:00-22:00" />
        <input value={restaurantProfile.workingHours.fri} onChange={(e) => setRestaurantProfile((s) => ({ ...s, workingHours: { ...s.workingHours, fri: e.target.value } }))} placeholder="Fri 09:00-22:00" />
        <input value={restaurantProfile.workingHours.sat} onChange={(e) => setRestaurantProfile((s) => ({ ...s, workingHours: { ...s.workingHours, sat: e.target.value } }))} placeholder="Sat 09:00-22:00" />
        <input value={restaurantProfile.workingHours.sun} onChange={(e) => setRestaurantProfile((s) => ({ ...s, workingHours: { ...s.workingHours, sun: e.target.value } }))} placeholder="Sun 09:00-22:00" />
        <button disabled={loading} type="submit">Save</button>
      </form>
    </section>
  )

  const renderItems = () => (
    <section className="panel">
      <div className="section-head">
        <h2>Dishes</h2>
        <button disabled={loading} type="button" onClick={() => setCreatingDish(true)}>Add dish</button>
      </div>
      <div className="filters-bar sticky-filters">
        <input value={dishSearch} onChange={(e) => setDishSearch(e.target.value)} placeholder="Search dishes" />
        <select value={selectedCategoryId} onChange={(e) => { setSelectedCategoryId(e.target.value); setItemForm((s) => ({ ...s, categoryId: e.target.value })) }}>
          <option value="">All categories</option>
          {categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        <select value={dishSort} onChange={(e) => setDishSort(e.target.value)}>
          <option value="name_asc">Name A-Z</option>
          <option value="name_desc">Name Z-A</option>
          <option value="price_asc">Price Low-High</option>
          <option value="price_desc">Price High-Low</option>
        </select>
      </div>
      <div className="table-wrap">
        {filteredDishes.length === 0 ? (
          <div className="empty-note">No dishes for selected filter.</div>
        ) : (
          <table className="items-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Category</th>
                <th>Old price</th>
                <th>New price</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredDishes.map((item) => (
                <tr key={item.id}>
                  <td>
                    <strong>{item.name}</strong>
                    {Array.isArray(item.recipe) && item.recipe.length > 0 && (
                      <ul className="recipe-list">
                        {item.recipe.map((part, index) => <li key={`${item.id}:recipe:${index}`}>{part}</li>)}
                      </ul>
                    )}
                  </td>
                  <td>{categoryNameById.get(item.categoryId) || 'Uncategorized'}</td>
                  <td>{item.discountIsActive ? Number(item.variants?.[0]?.priceMinor || 0).toLocaleString() : '-'}</td>
                  <td>
                    {Number((item.variants?.[0]?.priceMinor || 0) - (item.discountMinor || 0)).toLocaleString()}
                  </td>
                  <td>
                    <span className={`status-pill ${item.isAvailableNow ? 'on' : 'off'}`}>
                      {item.isAvailableNow ? 'available' : 'hidden'}
                    </span>
                  </td>
                  <td>
                    <div className="actions">
                      <button disabled={loading} type="button" onClick={() => openEditItem(item)}>Edit</button>
                      <button disabled={loading} type="button" onClick={() => onDuplicateItem(item)}>Copy</button>
                      <label className="switch">
                        <input
                          type="checkbox"
                          checked={Boolean(item.isAvailableNow)}
                          disabled={loading}
                          onChange={() => onToggleAvailability(item)}
                        />
                        <span>On</span>
                      </label>
                      <button disabled={loading} type="button" onClick={() => onDeleteItem(item)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {editingItem && (
        <div className="modal-backdrop" onClick={closeEditItem}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <h3>Edit Dish</h3>
            <form className="invite" onSubmit={onSaveEditItem}>
              <input value={editItemForm.name} onChange={(e) => setEditItemForm((s) => ({ ...s, name: e.target.value }))} placeholder="Dish name" required />
              <select value={editItemForm.categoryId} onChange={(e) => setEditItemForm((s) => ({ ...s, categoryId: e.target.value }))} required>
                <option value="">choose category</option>
                {categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
              <input value={editItemForm.oldPriceMinor} onChange={(e) => setEditItemForm((s) => ({ ...s, oldPriceMinor: e.target.value }))} placeholder="Old price" />
              <input value={editItemForm.newPriceMinor} onChange={(e) => setEditItemForm((s) => ({ ...s, newPriceMinor: e.target.value }))} placeholder="New price" required />
              <input value={editItemForm.image} onChange={(e) => setEditItemForm((s) => ({ ...s, image: e.target.value }))} placeholder="Photo URL" />
              <input type="file" accept="image/*" onChange={onPickEditImage} />
              {editItemForm.image && <img className="image-preview" src={editItemForm.image} alt="Dish preview" />}
              <input value={editItemForm.description} onChange={(e) => setEditItemForm((s) => ({ ...s, description: e.target.value }))} placeholder="Description" />
              <textarea value={editItemForm.recipeText} onChange={(e) => setEditItemForm((s) => ({ ...s, recipeText: e.target.value }))} placeholder={'Recipe ingredients, one per line\nbeef\ntomato\ncucumber'} rows={4} />
              <select value={String(editItemForm.isAvailableNow)} onChange={(e) => setEditItemForm((s) => ({ ...s, isAvailableNow: e.target.value === 'true' }))}>
                <option value="true">available</option>
                <option value="false">hidden</option>
              </select>
              <button disabled={loading} type="submit">Save</button>
            </form>
            <button className="close-btn" type="button" onClick={closeEditItem}>Close</button>
          </div>
        </div>
      )}

      {creatingDish && (
        <div className="modal-backdrop" onClick={() => setCreatingDish(false)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <h3>Add Dish</h3>
            <form className="invite" onSubmit={onCreateItem}>
              <input value={itemForm.name} onChange={(e) => setItemForm((s) => ({ ...s, name: e.target.value }))} placeholder="Dish name" required />
              <select value={itemForm.categoryId} onChange={(e) => setItemForm((s) => ({ ...s, categoryId: e.target.value }))} required>
                <option value="">choose category</option>
                {categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
              <input value={itemForm.oldPriceMinor} onChange={(e) => setItemForm((s) => ({ ...s, oldPriceMinor: e.target.value }))} placeholder="Old price" />
              <input value={itemForm.newPriceMinor} onChange={(e) => setItemForm((s) => ({ ...s, newPriceMinor: e.target.value }))} placeholder="New price" required />
              <input value={itemForm.image} onChange={(e) => setItemForm((s) => ({ ...s, image: e.target.value }))} placeholder="Photo URL" />
              <input type="file" accept="image/*" onChange={onPickCreateImage} />
              {itemForm.image && <img className="image-preview" src={itemForm.image} alt="Dish preview" />}
              <input value={itemForm.description} onChange={(e) => setItemForm((s) => ({ ...s, description: e.target.value }))} placeholder="Description" />
              <textarea value={itemForm.recipeText} onChange={(e) => setItemForm((s) => ({ ...s, recipeText: e.target.value }))} placeholder={'Recipe ingredients, one per line\nbeef\ntomato\ncucumber'} rows={4} />
              <button disabled={loading} type="submit">Create</button>
            </form>
            <button className="close-btn" type="button" onClick={() => setCreatingDish(false)}>Close</button>
          </div>
        </div>
      )}

      {deleteCandidate && (
        <div className="modal-backdrop" onClick={() => setDeleteCandidate(null)}>
          <div className="modal modal-compact" onClick={(event) => event.stopPropagation()}>
            <h3>Delete Dish</h3>
            <p>Delete "{deleteCandidate.name}"?</p>
            <div className="actions">
              <button disabled={loading} type="button" onClick={onConfirmDeleteItem}>Delete</button>
              <button className="close-btn" type="button" onClick={() => setDeleteCandidate(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </section>
  )

  const logout = () => {
    localStorage.removeItem('adminAccessToken')
    localStorage.removeItem('adminPrincipal')
    setPrincipal(null)
    setTab('restaurants')
    toast('idle', 'Signed out')
  }

  return (
    <main className="shell shell-wide">
      <aside className="sidebar panel">
        <h2>Admin</h2>
        <p className={`status ${status}`}>{message}</p>
        {principal && (
          <>
            <p><strong>{principal.role}</strong></p>
            <button onClick={logout} type="button">Sign out</button>
          </>
        )}
        <nav className="nav-list">
          {availableTabs.map((key) => (
            <button key={key} className={tab === key ? 'active' : ''} type="button" onClick={() => setTab(key)}>
              {key === 'restaurants' && 'Restaurants'}
              {key === 'restaurant' && 'Restaurant Info'}
              {key === 'staff' && 'Staff'}
              {key === 'categories' && 'Categories'}
              {key === 'items' && 'Dishes'}
            </button>
          ))}
        </nav>
      </aside>

      <section>
        {tab === 'restaurants' && renderRestaurants()}
        {tab === 'restaurant' && renderRestaurantProfile()}
        {tab === 'staff' && renderStaff()}
        {tab === 'categories' && renderCategories()}
        {tab === 'items' && renderItems()}
      </section>
    </main>
  )
}

export default App
