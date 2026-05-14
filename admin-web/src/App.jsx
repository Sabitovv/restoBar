import { useEffect, useMemo, useState } from 'react'
import './App.css'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
const MAX_IMAGE_FILE_BYTES = 3 * 1024 * 1024
const MAX_IMAGE_EDGE = 1600
const WEEK_DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
const DAY_LABELS = { mon: 'Понедельник', tue: 'Вторник', wed: 'Среда', thu: 'Четверг', fri: 'Пятница', sat: 'Суббота', sun: 'Воскресенье' }

const createDefaultWorkingHours = () => ({
  mon: { isOpen: true, openAt: '09:00', closeAt: '22:00' },
  tue: { isOpen: true, openAt: '09:00', closeAt: '22:00' },
  wed: { isOpen: true, openAt: '09:00', closeAt: '22:00' },
  thu: { isOpen: true, openAt: '09:00', closeAt: '22:00' },
  fri: { isOpen: true, openAt: '09:00', closeAt: '22:00' },
  sat: { isOpen: true, openAt: '09:00', closeAt: '22:00' },
  sun: { isOpen: true, openAt: '09:00', closeAt: '22:00' },
})

function App() {
  const [principal, setPrincipal] = useState(() => {
    const saved = localStorage.getItem('adminPrincipal')
    return saved ? JSON.parse(saved) : null
  })
  const [status, setStatus] = useState('idle')
  const [message, setMessage] = useState('Откройте панель из Telegram-бота кнопкой Open Admin.')
  const [tab, setTab] = useState('restaurants')
  const [loading, setLoading] = useState(false)

  const [restaurants, setRestaurants] = useState([])
  const [staffItems, setStaffItems] = useState([])
  const [categories, setCategories] = useState([])
  const [menuItems, setMenuItems] = useState([])
  const [restaurantProfile, setRestaurantProfile] = useState({
    name: '',
    about: '',
    aboutI18n: { kk: '', ru: '', en: '' },
    previewImage: '',
    workingHours: createDefaultWorkingHours(),
  })

  const [selectedRestaurantId, setSelectedRestaurantId] = useState('')
  const [selectedCategoryId, setSelectedCategoryId] = useState('')
  const [categorySearch, setCategorySearch] = useState('')
  const [dishSearch, setDishSearch] = useState('')
  const [dishSort, setDishSort] = useState('name_asc')

  const [restaurantForm, setRestaurantForm] = useState({ name: '', slug: '' })
  const [inviteForm, setInviteForm] = useState({ username: '', role: 'admin', restaurantId: '' })
  const [categoryForm, setCategoryForm] = useState({
    name: '',
    nameI18n: { kk: '', ru: '', en: '' },
    image: '',
    isActive: true,
  })
  const [itemForm, setItemForm] = useState({
    name: '',
    nameI18n: { kk: '', ru: '', en: '' },
    categoryId: '',
    oldPriceMinor: '',
    newPriceMinor: '500',
    description: '',
    descriptionI18n: { kk: '', ru: '', en: '' },
    recipeText: '',
    recipeI18n: { kk: '', ru: '', en: '' },
    image: '',
    isAvailableNow: true,
  })
  const [editingItem, setEditingItem] = useState(null)
  const [editingCategory, setEditingCategory] = useState(null)
  const [draggingCategoryId, setDraggingCategoryId] = useState('')
  const [creatingCategory, setCreatingCategory] = useState(false)
  const [creatingDish, setCreatingDish] = useState(false)
  const [createDishStep, setCreateDishStep] = useState(1)
  const [editDishStep, setEditDishStep] = useState(1)
  const [editItemForm, setEditItemForm] = useState({
    id: '',
    name: '',
    nameI18n: { kk: '', ru: '', en: '' },
    categoryId: '',
    oldPriceMinor: '',
    newPriceMinor: '0',
    description: '',
    descriptionI18n: { kk: '', ru: '', en: '' },
    recipeText: '',
    recipeI18n: { kk: '', ru: '', en: '' },
    image: '',
    isAvailableNow: true,
  })
  const [deleteCandidate, setDeleteCandidate] = useState(null)
  const [editCategoryForm, setEditCategoryForm] = useState({
    id: '',
    name: '',
    nameI18n: { kk: '', ru: '', en: '' },
    image: '',
    isActive: true,
  })

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
    if (!hasOld && !hasNew) throw new Error('Укажите старую цену, новую цену или обе.')

    const oldPrice = hasOld ? Number(oldValue) : null
    const newPrice = hasNew ? Number(newValue) : null
    if (oldPrice !== null && !(oldPrice > 0)) throw new Error('Старая цена должна быть больше 0.')
    if (newPrice !== null && !(newPrice > 0)) throw new Error('Новая цена должна быть больше 0.')

    if (oldPrice !== null && newPrice !== null) {
      if (newPrice > oldPrice) throw new Error('Новая цена не может быть больше старой.')
      if (newPrice === oldPrice) return { priceMinor: oldPrice, discountMinor: 0, discountIsActive: false }
      return { priceMinor: oldPrice, discountMinor: oldPrice - newPrice, discountIsActive: true }
    }

    const priceMinor = oldPrice ?? newPrice
    return { priceMinor, discountMinor: 0, discountIsActive: false }
  }

  const validateRuBaseText = (i18n, fieldLabel) => {
    const ru = String(i18n?.ru || '').trim()
    const kk = String(i18n?.kk || '').trim()
    const en = String(i18n?.en || '').trim()
    if ((kk || en) && !ru) {
      throw new Error(`${fieldLabel}: сначала заполните RU, потом KK/EN.`)
    }
  }

  const getStepOneError = (form) => {
    const nameRu = String(form.nameI18n?.ru || form.name || '').trim()
    const hasOld = String(form.oldPriceMinor || '').trim() !== ''
    const hasNew = String(form.newPriceMinor || '').trim() !== ''
    if (!nameRu) return 'Fill Dish name (RU).'
    if (!form.categoryId) return 'Choose category.'
    if (!hasOld && !hasNew) return 'Fill price KZT.'
    const oldPrice = hasOld ? Number(form.oldPriceMinor) : null
    const newPrice = hasNew ? Number(form.newPriceMinor) : null
    if (oldPrice !== null && !(oldPrice > 0)) return 'Old price must be > 0.'
    if (newPrice !== null && !(newPrice > 0)) return 'New price must be > 0.'
    if (oldPrice !== null && newPrice !== null && newPrice > oldPrice) return 'New price cannot be greater than old price.'
    return ''
  }

  const canContinueFromStepOne = (form) => !getStepOneError(form)

  const roleLabel = (role) => {
    if (role === 'super_admin') return 'супер-админ'
    if (role === 'admin') return 'админ'
    if (role === 'manager') return 'менеджер'
    return role || '-'
  }

  const staffStatusLabel = (status) => {
    if (status === 'active') return 'активен'
    if (status === 'pending') return 'ожидает'
    if (status === 'revoked') return 'отозван'
    if (status === 'inactive') return 'неактивен'
    return status || '-'
  }

  const ruTextInputProps = {
    lang: 'ru',
    inputMode: 'text',
    autoCapitalize: 'off',
    autoCorrect: 'off',
    autoComplete: 'off',
    spellCheck: false,
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
      throw new Error(payload.message || 'Ошибка запроса')
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
    reader.onerror = () => reject(new Error('Не удалось прочитать выбранный файл.'))
    reader.readAsDataURL(file)
  })

  const loadImageFromDataUrl = (dataUrl) => new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('Не удалось загрузить изображение.'))
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
    if (!context) throw new Error('Не удалось подготовить сжатие изображения.')
    context.drawImage(image, 0, 0, targetWidth, targetHeight)

    let quality = 0.86
    let output = canvas.toDataURL('image/jpeg', quality)
    while (output.length > 4_500_000 && quality > 0.45) {
      quality -= 0.08
      output = canvas.toDataURL('image/jpeg', quality)
    }
    if (output.length > 4_500_000) {
      throw new Error('Изображение все еще слишком большое после сжатия. Выберите файл меньше.')
    }
    return output
  }

  useEffect(() => {
    const webApp = window.Telegram?.WebApp
    webApp?.ready()
    const initData = webApp?.initData
    if (!initData) {
      setStatus('error')
      setMessage('Откройте панель из Telegram-бота кнопкой Open Admin.')
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
        if (!response.ok) throw new Error(payload.message || 'Ошибка авторизации')
        localStorage.setItem('adminAccessToken', payload.accessToken)
        localStorage.setItem('adminPrincipal', JSON.stringify(payload.principal))
        setPrincipal(payload.principal)
        toast('success', 'Доступ подтвержден.')
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
    const nextWorkingHours = createDefaultWorkingHours()
    WEEK_DAYS.forEach((day) => {
      const value = data.workingHours?.[day]
      if (value && typeof value === 'object') {
        nextWorkingHours[day] = {
          isOpen: Boolean(value.isOpen),
          openAt: value.openAt || '09:00',
          closeAt: value.closeAt || '22:00',
        }
      }
    })
    setRestaurantProfile({
      name: data.name || '',
      about: data.about || '',
      aboutI18n: {
        kk: data.aboutI18n?.kk || '',
        ru: data.aboutI18n?.ru || data.about || '',
        en: data.aboutI18n?.en || '',
      },
      previewImage: data.previewImage || '',
      workingHours: nextWorkingHours,
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
      toast('success', 'Ресторан создан.')
      const data = await api('/admin/restaurants')
      setRestaurants(data.items || [])
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const onDeleteRestaurant = async (id) => {
    if (!window.confirm('Удалить ресторан? Он станет неактивным.')) return
    setLoading(true)
    try {
      await api(`/admin/restaurants/${id}`, { method: 'DELETE' })
      toast('success', 'Ресторан переведен в неактивный.')
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
      toast('success', 'Приглашение создано.')
      await loadStaff()
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const onRevokeStaff = async (id) => {
    if (!window.confirm('Отозвать доступ?')) return
    setLoading(true)
    try {
      await api(`/admin/staff/${id}`, { method: 'DELETE' })
      toast('success', 'Доступ отозван.')
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
      const ruName = String(categoryForm.nameI18n.ru || '').trim()
      if (!ruName) throw new Error('Название категории (RU) обязательно.')
      await api('/admin/menu/categories', {
        method: 'POST',
        body: JSON.stringify({
          ...categoryForm,
          name: ruName,
          nameI18n: {
            kk: categoryForm.nameI18n.kk,
            ru: ruName,
            en: categoryForm.nameI18n.en,
          },
        }),
      })
      setCategoryForm({ name: '', nameI18n: { kk: '', ru: '', en: '' }, image: '', isActive: true })
      toast('success', 'Категория создана.')
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
      nameI18n: {
        kk: category.nameI18n?.kk || '',
        ru: category.nameI18n?.ru || category.name || '',
        en: category.nameI18n?.en || '',
      },
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
      const ruName = String(editCategoryForm.nameI18n.ru || '').trim()
      if (!ruName) throw new Error('Название категории (RU) обязательно.')
      await api(`/admin/menu/categories/${editCategoryForm.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          name: ruName,
          nameI18n: {
            kk: editCategoryForm.nameI18n.kk,
            ru: ruName,
            en: editCategoryForm.nameI18n.en,
          },
          image: editCategoryForm.image,
          isActive: editCategoryForm.isActive,
        }),
      })
      toast('success', 'Категория обновлена.')
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
      toast('error', 'Изображение слишком большое. Максимум 3 МБ.')
      event.target.value = ''
      return
    }
    try {
      const dataUrl = await fileToDataUrl(file)
      const compressed = await compressImageDataUrl(dataUrl)
      setCategoryForm((state) => ({ ...state, image: compressed }))
      toast('success', 'Изображение категории выбрано и сжато.')
    } catch (error) {
      toast('error', error.message)
    }
  }

  const onPickEditCategoryImage = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (file.size > MAX_IMAGE_FILE_BYTES) {
      toast('error', 'Изображение слишком большое. Максимум 3 МБ.')
      event.target.value = ''
      return
    }
    try {
      const dataUrl = await fileToDataUrl(file)
      const compressed = await compressImageDataUrl(dataUrl)
      setEditCategoryForm((state) => ({ ...state, image: compressed }))
      toast('success', 'Изображение категории выбрано и сжато.')
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
      toast('success', 'Порядок категорий сохранен.')
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
      const ruName = String(itemForm.nameI18n.ru || '').trim()
      if (!ruName) throw new Error('Название блюда (RU) обязательно.')
      if (!itemForm.categoryId) throw new Error('Категория обязательна.')
      validateRuBaseText(itemForm.nameI18n, 'Название блюда')
      validateRuBaseText(itemForm.descriptionI18n, 'Описание блюда')
      validateRuBaseText(itemForm.recipeI18n, 'Рецепт блюда')

      await api('/admin/menu/items', {
        method: 'POST',
        body: JSON.stringify({
          name: ruName,
          nameI18n: {
            kk: itemForm.nameI18n.kk,
            ru: ruName,
            en: itemForm.nameI18n.en,
          },
          categoryId: itemForm.categoryId,
          description: itemForm.description,
          descriptionI18n: {
            kk: itemForm.descriptionI18n.kk,
            ru: itemForm.descriptionI18n.ru || itemForm.description,
            en: itemForm.descriptionI18n.en,
          },
          recipe: parseRecipe(itemForm.recipeText),
          recipeI18n: {
            kk: parseRecipe(itemForm.recipeI18n.kk),
            ru: parseRecipe(itemForm.recipeI18n.ru || itemForm.recipeText),
            en: parseRecipe(itemForm.recipeI18n.en),
          },
          image: itemForm.image,
          priceByCurrency: { KZT: priceData.priceMinor },
          discountMinor: priceData.discountMinor,
          discountIsActive: priceData.discountIsActive,
          isAvailableNow: itemForm.isAvailableNow,
          variants: [{ name: 'default', priceMinor: priceData.priceMinor, currency: 'KZT' }],
        }),
      })
      setItemForm((state) => ({ ...state, name: '', nameI18n: { kk: '', ru: '', en: '' }, description: '', descriptionI18n: { kk: '', ru: '', en: '' }, recipeText: '', recipeI18n: { kk: '', ru: '', en: '' }, image: '', oldPriceMinor: '', newPriceMinor: '500' }))
      toast('success', 'Блюдо создано.')
      setCreatingDish(false)
      setCreateDishStep(1)
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
      toast('error', 'Изображение слишком большое. Максимум 3 МБ.')
      event.target.value = ''
      return
    }
    try {
      const dataUrl = await fileToDataUrl(file)
      const compressed = await compressImageDataUrl(dataUrl)
      setItemForm((state) => ({ ...state, image: compressed }))
      toast('success', 'Изображение выбрано и сжато.')
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
      toast('success', 'Статус доступности обновлен.')
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
      toast('success', 'Блюдо удалено.')
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
            currency: item.variants?.[0]?.currency || 'KZT',
          }],
        }),
      })
      toast('success', 'Блюдо скопировано.')
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
      nameI18n: {
        kk: item.nameI18n?.kk || '',
        ru: item.nameI18n?.ru || item.name || '',
        en: item.nameI18n?.en || '',
      },
      categoryId: item.categoryId || '',
      oldPriceMinor: discount > 0 ? String(basePrice) : '',
      newPriceMinor: String(effectivePrice || 0),
      description: item.description || '',
      descriptionI18n: {
        kk: item.descriptionI18n?.kk || '',
        ru: item.descriptionI18n?.ru || item.description || '',
        en: item.descriptionI18n?.en || '',
      },
      recipeText: Array.isArray(item.recipe) ? item.recipe.join('\n') : (item.recipe || ''),
      recipeI18n: {
        kk: Array.isArray(item.recipeI18n?.kk) ? item.recipeI18n.kk.join('\n') : '',
        ru: Array.isArray(item.recipeI18n?.ru) ? item.recipeI18n.ru.join('\n') : (Array.isArray(item.recipe) ? item.recipe.join('\n') : (item.recipe || '')),
        en: Array.isArray(item.recipeI18n?.en) ? item.recipeI18n.en.join('\n') : '',
      },
      image: item.image || '',
      isAvailableNow: Boolean(item.isAvailableNow),
    })
    setEditDishStep(1)
  }

  const closeEditItem = () => {
    setEditingItem(null)
    setEditDishStep(1)
  }

  const closeCreateItem = () => {
    setCreatingDish(false)
    setCreateDishStep(1)
  }

  const onSaveEditItem = async (event) => {
    event.preventDefault()
    setLoading(true)
    try {
      const priceData = splitPrices(editItemForm.oldPriceMinor, editItemForm.newPriceMinor)
      const ruName = String(editItemForm.nameI18n.ru || '').trim()
      if (!ruName) throw new Error('Название блюда (RU) обязательно.')
      if (!editItemForm.categoryId) throw new Error('Категория обязательна.')
      validateRuBaseText(editItemForm.nameI18n, 'Название блюда')
      validateRuBaseText(editItemForm.descriptionI18n, 'Описание блюда')
      validateRuBaseText(editItemForm.recipeI18n, 'Рецепт блюда')

      await api(`/admin/menu/items/${editItemForm.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          name: ruName,
          nameI18n: {
            kk: editItemForm.nameI18n.kk,
            ru: ruName,
            en: editItemForm.nameI18n.en,
          },
          categoryId: editItemForm.categoryId,
          discountMinor: priceData.discountMinor,
          discountIsActive: priceData.discountIsActive,
          description: editItemForm.description,
          descriptionI18n: {
            kk: editItemForm.descriptionI18n.kk,
            ru: editItemForm.descriptionI18n.ru || editItemForm.description,
            en: editItemForm.descriptionI18n.en,
          },
          recipe: parseRecipe(editItemForm.recipeText),
          recipeI18n: {
            kk: parseRecipe(editItemForm.recipeI18n.kk),
            ru: parseRecipe(editItemForm.recipeI18n.ru || editItemForm.recipeText),
            en: parseRecipe(editItemForm.recipeI18n.en),
          },
          image: editItemForm.image,
          priceByCurrency: { KZT: priceData.priceMinor },
          isAvailableNow: editItemForm.isAvailableNow,
          variants: [{ name: 'default', priceMinor: priceData.priceMinor, currency: 'KZT' }],
        }),
      })
      toast('success', 'Блюдо обновлено.')
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
      toast('error', 'Изображение слишком большое. Максимум 3 МБ.')
      event.target.value = ''
      return
    }
    try {
      const dataUrl = await fileToDataUrl(file)
      const compressed = await compressImageDataUrl(dataUrl)
      setEditItemForm((state) => ({ ...state, image: compressed }))
      toast('success', 'Изображение выбрано и сжато.')
    } catch (error) {
      toast('error', error.message)
    }
  }

  const onPickRestaurantPreview = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (file.size > MAX_IMAGE_FILE_BYTES) {
      toast('error', 'Изображение слишком большое. Максимум 3 МБ.')
      event.target.value = ''
      return
    }
    try {
      const dataUrl = await fileToDataUrl(file)
      const compressed = await compressImageDataUrl(dataUrl)
      setRestaurantProfile((state) => ({ ...state, previewImage: compressed }))
      toast('success', 'Превью изображения выбрано и сжато.')
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
      toast('success', 'Профиль ресторана обновлен.')
      await loadRestaurantProfile()
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const translateRuText = async (text) => {
    const value = String(text || '').trim()
    if (!value) throw new Error('Сначала заполните русский текст.')
    const data = await api('/admin/i18n/translate', {
      method: 'POST',
      body: JSON.stringify({ text: value, sourceLang: 'ru', targets: ['kk', 'en'] }),
    })
    return {
      kk: data.translations?.kk || '',
      en: data.translations?.en || '',
      ru: value,
    }
  }

  const onTranslateCategoryNameCreate = async () => {
    setLoading(true)
    try {
      const translated = await translateRuText(categoryForm.nameI18n.ru)
      setCategoryForm((state) => ({ ...state, nameI18n: { ...state.nameI18n, ...translated }, name: translated.ru }))
      toast('success', 'Категория переведена на kk/en.')
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const onTranslateCategoryNameEdit = async () => {
    setLoading(true)
    try {
      const translated = await translateRuText(editCategoryForm.nameI18n.ru)
      setEditCategoryForm((state) => ({ ...state, nameI18n: { ...state.nameI18n, ...translated }, name: translated.ru }))
      toast('success', 'Категория переведена на kk/en.')
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const onTranslateDishCreate = async () => {
    setLoading(true)
    try {
      const nameTranslated = await translateRuText(itemForm.nameI18n.ru)
      const descriptionTranslated = await translateRuText(itemForm.descriptionI18n.ru || itemForm.description)
      const recipeTranslated = await translateRuText(itemForm.recipeI18n.ru || itemForm.recipeText)
      setItemForm((state) => ({
        ...state,
        name: nameTranslated.ru,
        description: descriptionTranslated.ru,
        recipeText: recipeTranslated.ru,
        nameI18n: { ...state.nameI18n, ...nameTranslated },
        descriptionI18n: { ...state.descriptionI18n, ...descriptionTranslated },
        recipeI18n: { ...state.recipeI18n, ...recipeTranslated },
      }))
      toast('success', 'Блюдо переведено на kk/en.')
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const onTranslateDishEdit = async () => {
    setLoading(true)
    try {
      const nameTranslated = await translateRuText(editItemForm.nameI18n.ru)
      const descriptionTranslated = await translateRuText(editItemForm.descriptionI18n.ru || editItemForm.description)
      const recipeTranslated = await translateRuText(editItemForm.recipeI18n.ru || editItemForm.recipeText)
      setEditItemForm((state) => ({
        ...state,
        name: nameTranslated.ru,
        description: descriptionTranslated.ru,
        recipeText: recipeTranslated.ru,
        nameI18n: { ...state.nameI18n, ...nameTranslated },
        descriptionI18n: { ...state.descriptionI18n, ...descriptionTranslated },
        recipeI18n: { ...state.recipeI18n, ...recipeTranslated },
      }))
      toast('success', 'Блюдо переведено на kk/en.')
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const onTranslateRestaurantAbout = async () => {
    const text = (restaurantProfile.aboutI18n?.ru || restaurantProfile.about || '').trim()
    if (!text) return toast('error', 'Сначала заполните русский текст описания.')
    setLoading(true)
    try {
      const data = await api('/admin/i18n/translate', {
        method: 'POST',
        body: JSON.stringify({ text, sourceLang: 'ru', targets: ['kk', 'en'] }),
      })
      setRestaurantProfile((state) => ({
        ...state,
        aboutI18n: {
          ...state.aboutI18n,
          kk: data.translations?.kk || state.aboutI18n.kk,
          en: data.translations?.en || state.aboutI18n.en,
          ru: text,
        },
      }))
      toast('success', 'Описание переведено на kk/en.')
    } catch (error) {
      toast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const renderRestaurants = () => (
    <section className="panel">
      <h2>Рестораны</h2>
      <form className="invite" onSubmit={onCreateRestaurant}>
        <input value={restaurantForm.name} onChange={(e) => setRestaurantForm((s) => ({ ...s, name: e.target.value }))} placeholder="Название ресторана" required />
        <input value={restaurantForm.slug} onChange={(e) => setRestaurantForm((s) => ({ ...s, slug: e.target.value }))} placeholder="slug" required />
        <button disabled={loading} type="submit">Добавить ресторан</button>
      </form>
      <div className="staff-list">
        {restaurants.length === 0 && <article><strong>Пусто</strong><span>Ресторанов пока нет.</span></article>}
        {restaurants.map((item) => (
          <article key={item.id}>
            <strong>{item.name}</strong>
            <span>{item.slug}</span>
            <span>{item.isActive ? 'активен' : 'неактивен'}</span>
            <div className="actions"><button disabled={loading} type="button" onClick={() => onDeleteRestaurant(item.id)}>Удалить</button></div>
          </article>
        ))}
      </div>
    </section>
  )

  const renderStaff = () => (
    <section className="panel">
      <h2>Персонал</h2>
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
        <input value={inviteForm.username} onChange={(e) => setInviteForm((s) => ({ ...s, username: e.target.value }))} placeholder="Username в Telegram" required />
        <select value={inviteForm.role} onChange={(e) => setInviteForm((s) => ({ ...s, role: e.target.value }))}>
          {isSuper ? <option value="admin">админ</option> : <option value="manager">менеджер</option>}
        </select>
        {isSuper ? (
          <select value={inviteForm.restaurantId} onChange={(e) => setInviteForm((s) => ({ ...s, restaurantId: e.target.value }))}>
            {restaurants.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        ) : <span />}
        <button disabled={loading} type="submit">Пригласить</button>
      </form>
      <div className="staff-list">
        {staffItems.length === 0 && <article><strong>Пусто</strong><span>В выбранном ресторане нет персонала.</span></article>}
        {staffItems.map((item) => (
          <article key={item.id}>
            <strong>@{item.username || 'unknown'}</strong>
            <span>{roleLabel(item.role)}</span>
            <span>{staffStatusLabel(item.status)}</span>
            <div className="actions"><button disabled={loading} type="button" onClick={() => onRevokeStaff(item.id)}>Отозвать</button></div>
          </article>
        ))}
      </div>
    </section>
  )

  const renderCategories = () => (
    <section className="panel">
      <div className="section-head">
        <h2>Категории</h2>
        <button disabled={loading} type="button" onClick={() => setCreatingCategory(true)}>Добавить категорию</button>
      </div>
      <div className="category-toolbar">
        <input
          value={categorySearch}
          onChange={(e) => setCategorySearch(e.target.value)}
          placeholder="Поиск категорий"
        />
        <span className="category-count">Найдено: {filteredCategories.length}</span>
      </div>
      <div className="category-grid">
        {filteredCategories.length === 0 && <article className="category-card"><strong>Пусто</strong><span>Категории не найдены.</span></article>}
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
              <span className={`status-pill ${item.isActive ? 'on' : 'off'}`}>{item.isActive ? 'активна' : 'неактивна'}</span>
            </div>
            <span className="category-meta">{item.itemsCount} блюд</span>
            <div className="actions">
              <button disabled={loading} type="button" onClick={() => openEditCategory(item)}>Изменить</button>
            </div>
          </article>
        ))}
      </div>

      {editingCategory && (
        <div className="modal-backdrop" onClick={closeEditCategory}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <h3>Изменить категорию</h3>
            <form className="invite" onSubmit={onSaveEditCategory}>
              <input {...ruTextInputProps} value={editCategoryForm.nameI18n.ru} onChange={(e) => setEditCategoryForm((s) => ({ ...s, name: e.target.value, nameI18n: { ...s.nameI18n, ru: e.target.value } }))} placeholder="Название категории (RU)" required />
              <button disabled={loading} type="button" onClick={onTranslateCategoryNameEdit}>{'Перевести RU в KK/EN'}</button>
              <input value={editCategoryForm.nameI18n.kk} onChange={(e) => setEditCategoryForm((s) => ({ ...s, nameI18n: { ...s.nameI18n, kk: e.target.value } }))} placeholder="Название категории (KK)" />
              <input value={editCategoryForm.nameI18n.en} onChange={(e) => setEditCategoryForm((s) => ({ ...s, nameI18n: { ...s.nameI18n, en: e.target.value } }))} placeholder="Название категории (EN)" />
              <input type="file" accept="image/*" onChange={onPickEditCategoryImage} />
              {editCategoryForm.image && <img className="image-preview" src={editCategoryForm.image} alt="Category preview" />}
              <select value={String(editCategoryForm.isActive)} onChange={(e) => setEditCategoryForm((s) => ({ ...s, isActive: e.target.value === 'true' }))}>
                <option value="true">активна</option>
                <option value="false">неактивна</option>
              </select>
              <button disabled={loading} type="submit">Сохранить</button>
            </form>
            <button className="close-btn" type="button" onClick={closeEditCategory}>Закрыть</button>
          </div>
        </div>
      )}

      {creatingCategory && (
        <div className="modal-backdrop" onClick={() => setCreatingCategory(false)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <h3>Добавить категорию</h3>
            <form className="invite" onSubmit={onCreateCategory}>
              <input {...ruTextInputProps} value={categoryForm.nameI18n.ru} onChange={(e) => setCategoryForm((s) => ({ ...s, name: e.target.value, nameI18n: { ...s.nameI18n, ru: e.target.value } }))} placeholder="Название категории (RU)" required />
              <button disabled={loading} type="button" onClick={onTranslateCategoryNameCreate}>{'Перевести RU в KK/EN'}</button>
              <input value={categoryForm.nameI18n.kk} onChange={(e) => setCategoryForm((s) => ({ ...s, nameI18n: { ...s.nameI18n, kk: e.target.value } }))} placeholder="Название категории (KK)" />
              <input value={categoryForm.nameI18n.en} onChange={(e) => setCategoryForm((s) => ({ ...s, nameI18n: { ...s.nameI18n, en: e.target.value } }))} placeholder="Название категории (EN)" />
              <input type="file" accept="image/*" onChange={onPickCreateCategoryImage} />
              {categoryForm.image && <img className="image-preview" src={categoryForm.image} alt="Category preview" />}
              <select value={String(categoryForm.isActive)} onChange={(e) => setCategoryForm((s) => ({ ...s, isActive: e.target.value === 'true' }))}>
                <option value="true">активна</option>
                <option value="false">неактивна</option>
              </select>
              <button disabled={loading} type="submit">Создать</button>
            </form>
            <button className="close-btn" type="button" onClick={() => setCreatingCategory(false)}>Закрыть</button>
          </div>
        </div>
      )}
    </section>
  )

  const renderRestaurantProfile = () => (
    <section className="panel restaurant-profile-panel">
      <div className="section-head"><h2>Информация о ресторане</h2></div>
      <p className="restaurant-profile-note">Заполните профиль аккуратно: эти данные видят гости в Mini App.</p>
      <form className="restaurant-profile-form" onSubmit={onSaveRestaurantProfile}>
        <section className="profile-card">
          <h3>Основное</h3>
          <div className="profile-card-grid">
            <input value={restaurantProfile.name} onChange={(e) => setRestaurantProfile((s) => ({ ...s, name: e.target.value }))} placeholder="Название ресторана" required />
            <input type="file" accept="image/*" onChange={onPickRestaurantPreview} />
          </div>
          {restaurantProfile.previewImage && <img className="image-preview" src={restaurantProfile.previewImage} alt="Restaurant preview" />}
        </section>

        <section className="profile-card">
          <h3>О ресторане</h3>
          <textarea
            {...ruTextInputProps}
            value={restaurantProfile.aboutI18n.ru}
            onChange={(e) => setRestaurantProfile((s) => ({ ...s, about: e.target.value, aboutI18n: { ...s.aboutI18n, ru: e.target.value } }))}
            placeholder="Описание (RU)"
            rows={3}
          />
          <button disabled={loading} type="button" onClick={onTranslateRestaurantAbout}>{'Перевести RU в KK/EN'}</button>
          <div className="profile-card-grid">
            <textarea
              value={restaurantProfile.aboutI18n.kk}
              onChange={(e) => setRestaurantProfile((s) => ({ ...s, aboutI18n: { ...s.aboutI18n, kk: e.target.value } }))}
              placeholder="Описание (KK)"
              rows={3}
            />
            <textarea
              value={restaurantProfile.aboutI18n.en}
              onChange={(e) => setRestaurantProfile((s) => ({ ...s, aboutI18n: { ...s.aboutI18n, en: e.target.value } }))}
              placeholder="Описание (EN)"
              rows={3}
            />
          </div>
        </section>

        <section className="profile-card">
          <h3>График работы</h3>
          <div className="hours-grid">
            {WEEK_DAYS.map((day) => (
              <article className="hours-day-card" key={day}>
                <div className="hours-day-head">
                  <strong>{DAY_LABELS[day] || day.toUpperCase()}</strong>
                  <label>
                    <input
                      type="checkbox"
                      checked={Boolean(restaurantProfile.workingHours?.[day]?.isOpen)}
                      onChange={(e) => setRestaurantProfile((s) => ({
                        ...s,
                        workingHours: {
                          ...s.workingHours,
                          [day]: {
                            ...(s.workingHours?.[day] || { isOpen: true, openAt: '09:00', closeAt: '22:00' }),
                            isOpen: e.target.checked,
                          },
                        },
                      }))}
                    />
                    Открыто
                  </label>
                </div>
                <div className="hours-time-grid">
                  <label className="hours-time-field">
                    <span>Открытие</span>
                    <input
                      type="time"
                      value={restaurantProfile.workingHours?.[day]?.openAt || '09:00'}
                      onChange={(e) => setRestaurantProfile((s) => ({
                        ...s,
                        workingHours: {
                          ...s.workingHours,
                          [day]: {
                            ...(s.workingHours?.[day] || { isOpen: true, openAt: '09:00', closeAt: '22:00' }),
                            openAt: e.target.value,
                          },
                        },
                      }))}
                    />
                  </label>
                  <label className="hours-time-field">
                    <span>Закрытие</span>
                    <input
                      type="time"
                      value={restaurantProfile.workingHours?.[day]?.closeAt || '22:00'}
                      onChange={(e) => setRestaurantProfile((s) => ({
                        ...s,
                        workingHours: {
                          ...s.workingHours,
                          [day]: {
                            ...(s.workingHours?.[day] || { isOpen: true, openAt: '09:00', closeAt: '22:00' }),
                            closeAt: e.target.value,
                          },
                        },
                      }))}
                    />
                  </label>
                </div>
              </article>
            ))}
          </div>
        </section>

        <div className="restaurant-profile-footer">
          <button disabled={loading} type="submit">Сохранить</button>
        </div>
      </form>
    </section>
  )

  const renderItems = () => (
    <section className="panel">
      <div className="section-head">
        <h2>Блюда</h2>
        <button disabled={loading} type="button" onClick={() => { setCreateDishStep(1); setCreatingDish(true) }}>Добавить блюдо</button>
      </div>
      <div className="filters-bar sticky-filters">
        <input value={dishSearch} onChange={(e) => setDishSearch(e.target.value)} placeholder="Поиск блюд" />
        <select value={selectedCategoryId} onChange={(e) => { setSelectedCategoryId(e.target.value); setItemForm((s) => ({ ...s, categoryId: e.target.value })) }}>
          <option value="">Все категории</option>
          {categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        <select value={dishSort} onChange={(e) => setDishSort(e.target.value)}>
          <option value="name_asc">Имя А-Я</option>
          <option value="name_desc">Имя Я-А</option>
          <option value="price_asc">Цена по возрастанию</option>
          <option value="price_desc">Цена по убыванию</option>
        </select>
      </div>
      <div className="table-wrap">
        {filteredDishes.length === 0 ? (
          <div className="empty-note">Нет блюд для выбранного фильтра.</div>
        ) : (
          <table className="items-table">
            <thead>
              <tr>
                <th>Название</th>
                <th>Категория</th>
                <th>Старая цена</th>
                <th>Новая цена</th>
                <th>Статус</th>
                <th>Действия</th>
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
                  <td>{categoryNameById.get(item.categoryId) || 'Без категории'}</td>
                  <td>{item.discountIsActive ? Number(item.variants?.[0]?.priceMinor || 0).toLocaleString() : '-'}</td>
                  <td>
                    {Number((item.variants?.[0]?.priceMinor || 0) - (item.discountMinor || 0)).toLocaleString()}
                  </td>
                  <td>
                    <span className={`status-pill ${item.isAvailableNow ? 'on' : 'off'}`}>
                      {item.isAvailableNow ? 'доступно' : 'скрыто'}
                    </span>
                  </td>
                  <td>
                    <div className="actions">
                      <button disabled={loading} type="button" onClick={() => openEditItem(item)}>Изменить</button>
                      <button disabled={loading} type="button" onClick={() => onDuplicateItem(item)}>Копировать</button>
                      <label className="switch">
                        <input
                          type="checkbox"
                          checked={Boolean(item.isAvailableNow)}
                          disabled={loading}
                          onChange={() => onToggleAvailability(item)}
                        />
                        <span>Вкл</span>
                      </label>
                      <button disabled={loading} type="button" onClick={() => onDeleteItem(item)}>Удалить</button>
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
          <div className="modal dish-wizard" onClick={(event) => event.stopPropagation()}>
            <h3>Изменить блюдо</h3>
            <p className="wizard-step-title">Шаг {editDishStep} из 4</p>
            <form className="invite" onSubmit={onSaveEditItem}>
              {editDishStep === 1 && (
                <>
                  <input {...ruTextInputProps} value={editItemForm.nameI18n.ru} onChange={(e) => setEditItemForm((s) => ({ ...s, name: e.target.value, nameI18n: { ...s.nameI18n, ru: e.target.value } }))} placeholder="Название блюда (RU)" required />
                  <select value={editItemForm.categoryId} onChange={(e) => setEditItemForm((s) => ({ ...s, categoryId: e.target.value }))} required>
                    <option value="">выберите категорию</option>
                    {categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                  <input value={editItemForm.oldPriceMinor} onChange={(e) => setEditItemForm((s) => ({ ...s, oldPriceMinor: e.target.value }))} placeholder="Старая цена (KZT)" />
                  <input value={editItemForm.newPriceMinor} onChange={(e) => setEditItemForm((s) => ({ ...s, newPriceMinor: e.target.value }))} placeholder="Новая цена (KZT)" required />
                  {!!getStepOneError(editItemForm) && <p className="wizard-error">{getStepOneError(editItemForm)}</p>}
                </>
              )}
              {editDishStep === 2 && (
                <>
                  <textarea {...ruTextInputProps} value={editItemForm.descriptionI18n.ru} onChange={(e) => setEditItemForm((s) => ({ ...s, description: e.target.value, descriptionI18n: { ...s.descriptionI18n, ru: e.target.value } }))} placeholder="Описание (RU)" rows={3} />
                  <textarea {...ruTextInputProps} value={editItemForm.recipeText} onChange={(e) => setEditItemForm((s) => ({ ...s, recipeText: e.target.value, recipeI18n: { ...s.recipeI18n, ru: e.target.value } }))} placeholder={'Recipe ingredients (RU), one per line\nbeef\ntomato\ncucumber'} rows={4} />
                </>
              )}
              {editDishStep === 3 && (
                <>
                  <button disabled={loading} type="button" onClick={onTranslateDishEdit}>{'Перевести RU в KK/EN'}</button>
                  <input value={editItemForm.nameI18n.kk} onChange={(e) => setEditItemForm((s) => ({ ...s, nameI18n: { ...s.nameI18n, kk: e.target.value } }))} placeholder="Dish name (KK)" />
                  <input value={editItemForm.nameI18n.en} onChange={(e) => setEditItemForm((s) => ({ ...s, nameI18n: { ...s.nameI18n, en: e.target.value } }))} placeholder="Dish name (EN)" />
                  <textarea value={editItemForm.descriptionI18n.kk} onChange={(e) => setEditItemForm((s) => ({ ...s, descriptionI18n: { ...s.descriptionI18n, kk: e.target.value } }))} placeholder="Description (KK)" rows={3} />
                  <textarea value={editItemForm.descriptionI18n.en} onChange={(e) => setEditItemForm((s) => ({ ...s, descriptionI18n: { ...s.descriptionI18n, en: e.target.value } }))} placeholder="Description (EN)" rows={3} />
                  <textarea value={editItemForm.recipeI18n.kk} onChange={(e) => setEditItemForm((s) => ({ ...s, recipeI18n: { ...s.recipeI18n, kk: e.target.value } }))} placeholder={'Recipe ingredients (KK), one per line'} rows={4} />
                  <textarea value={editItemForm.recipeI18n.en} onChange={(e) => setEditItemForm((s) => ({ ...s, recipeI18n: { ...s.recipeI18n, en: e.target.value } }))} placeholder={'Recipe ingredients (EN), one per line'} rows={4} />
                </>
              )}
              {editDishStep === 4 && (
                <>
                  <input type="file" accept="image/*" onChange={onPickEditImage} />
                  {editItemForm.image && <img className="image-preview" src={editItemForm.image} alt="Dish preview" />}
                  <select value={String(editItemForm.isAvailableNow)} onChange={(e) => setEditItemForm((s) => ({ ...s, isAvailableNow: e.target.value === 'true' }))}>
                    <option value="true">доступно</option>
                    <option value="false">скрыто</option>
                  </select>
                </>
              )}
              <div className="wizard-footer">
                <button type="button" className="close-btn" onClick={closeEditItem}>Закрыть</button>
                <button disabled={loading || editDishStep === 1} type="button" onClick={() => setEditDishStep((step) => Math.max(1, step - 1))}>Назад</button>
                {editDishStep < 4 ? (
                  <button disabled={loading || (editDishStep === 1 && !canContinueFromStepOne(editItemForm))} type="button" onClick={() => setEditDishStep((step) => Math.min(4, step + 1))}>Далее</button>
                ) : (
                  <button disabled={loading} type="submit">Сохранить</button>
                )}
              </div>
            </form>
          </div>
        </div>
      )}

      {creatingDish && (
        <div className="modal-backdrop" onClick={closeCreateItem}>
          <div className="modal dish-wizard" onClick={(event) => event.stopPropagation()}>
            <h3>Добавить блюдо</h3>
            <p className="wizard-step-title">Шаг {createDishStep} из 4</p>
            <form className="invite" onSubmit={onCreateItem}>
              {createDishStep === 1 && (
                <>
                  <input {...ruTextInputProps} value={itemForm.nameI18n.ru} onChange={(e) => setItemForm((s) => ({ ...s, name: e.target.value, nameI18n: { ...s.nameI18n, ru: e.target.value } }))} placeholder="Название блюда (RU)" required />
                  <select value={itemForm.categoryId} onChange={(e) => setItemForm((s) => ({ ...s, categoryId: e.target.value }))} required>
                    <option value="">выберите категорию</option>
                    {categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                  <input value={itemForm.oldPriceMinor} onChange={(e) => setItemForm((s) => ({ ...s, oldPriceMinor: e.target.value }))} placeholder="Старая цена (KZT)" />
                  <input value={itemForm.newPriceMinor} onChange={(e) => setItemForm((s) => ({ ...s, newPriceMinor: e.target.value }))} placeholder="Новая цена (KZT)" required />
                  {!!getStepOneError(itemForm) && <p className="wizard-error">{getStepOneError(itemForm)}</p>}
                </>
              )}
              {createDishStep === 2 && (
                <>
                  <textarea {...ruTextInputProps} value={itemForm.descriptionI18n.ru} onChange={(e) => setItemForm((s) => ({ ...s, description: e.target.value, descriptionI18n: { ...s.descriptionI18n, ru: e.target.value } }))} placeholder="Описание (RU)" rows={3} />
                  <textarea {...ruTextInputProps} value={itemForm.recipeText} onChange={(e) => setItemForm((s) => ({ ...s, recipeText: e.target.value, recipeI18n: { ...s.recipeI18n, ru: e.target.value } }))} placeholder={'Recipe ingredients (RU), one per line\nbeef\ntomato\ncucumber'} rows={4} />
                </>
              )}
              {createDishStep === 3 && (
                <>
                  <button disabled={loading} type="button" onClick={onTranslateDishCreate}>{'Перевести RU в KK/EN'}</button>
                  <input value={itemForm.nameI18n.kk} onChange={(e) => setItemForm((s) => ({ ...s, nameI18n: { ...s.nameI18n, kk: e.target.value } }))} placeholder="Dish name (KK)" />
                  <input value={itemForm.nameI18n.en} onChange={(e) => setItemForm((s) => ({ ...s, nameI18n: { ...s.nameI18n, en: e.target.value } }))} placeholder="Dish name (EN)" />
                  <textarea value={itemForm.descriptionI18n.kk} onChange={(e) => setItemForm((s) => ({ ...s, descriptionI18n: { ...s.descriptionI18n, kk: e.target.value } }))} placeholder="Description (KK)" rows={3} />
                  <textarea value={itemForm.descriptionI18n.en} onChange={(e) => setItemForm((s) => ({ ...s, descriptionI18n: { ...s.descriptionI18n, en: e.target.value } }))} placeholder="Description (EN)" rows={3} />
                  <textarea value={itemForm.recipeI18n.kk} onChange={(e) => setItemForm((s) => ({ ...s, recipeI18n: { ...s.recipeI18n, kk: e.target.value } }))} placeholder={'Recipe ingredients (KK), one per line'} rows={4} />
                  <textarea value={itemForm.recipeI18n.en} onChange={(e) => setItemForm((s) => ({ ...s, recipeI18n: { ...s.recipeI18n, en: e.target.value } }))} placeholder={'Recipe ingredients (EN), one per line'} rows={4} />
                </>
              )}
              {createDishStep === 4 && (
                <>
                  <input type="file" accept="image/*" onChange={onPickCreateImage} />
                  {itemForm.image && <img className="image-preview" src={itemForm.image} alt="Dish preview" />}
                  <p className="wizard-note">Можно сохранить без фото и добавить его позже.</p>
                </>
              )}
              <div className="wizard-footer">
                <button type="button" className="close-btn" onClick={closeCreateItem}>Закрыть</button>
                <button disabled={loading || createDishStep === 1} type="button" onClick={() => setCreateDishStep((step) => Math.max(1, step - 1))}>Назад</button>
                {createDishStep < 4 ? (
                  <button disabled={loading || (createDishStep === 1 && !canContinueFromStepOne(itemForm))} type="button" onClick={() => setCreateDishStep((step) => Math.min(4, step + 1))}>Далее</button>
                ) : (
                  <button disabled={loading} type="submit">Создать</button>
                )}
              </div>
            </form>
          </div>
        </div>
      )}

      {deleteCandidate && (
        <div className="modal-backdrop" onClick={() => setDeleteCandidate(null)}>
          <div className="modal modal-compact" onClick={(event) => event.stopPropagation()}>
            <h3>Удалить блюдо</h3>
            <p>Удалить "{deleteCandidate.name}"?</p>
            <div className="actions">
              <button disabled={loading} type="button" onClick={onConfirmDeleteItem}>Удалить</button>
              <button className="close-btn" type="button" onClick={() => setDeleteCandidate(null)}>Отмена</button>
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
    toast('idle', 'Вы вышли из аккаунта.')
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
              {key === 'restaurants' && 'Рестораны'}
              {key === 'restaurant' && 'Инфо ресторана'}
              {key === 'staff' && 'Персонал'}
              {key === 'categories' && 'Категории'}
              {key === 'items' && 'Блюда'}
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
