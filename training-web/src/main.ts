import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import App from './App.vue'
import router from './router'
import './styles/global.scss'

// Vant
import {
  Button, Cell, CellGroup, Icon, Tabbar, TabbarItem,
  NavBar, Form, Field, Toast, Dialog, Loading,
  Swipe, SwipeItem, Grid, GridItem, Tag, Progress,
  Card, Empty, Skeleton, PullRefresh, List,
  Search, Badge, Popup, ActionSheet, ShareSheet,
  Checkbox, Radio, RadioGroup, CheckboxGroup,
  Stepper, CountDown, Image as VanImage,
  Tab, Tabs, Sticky, Divider, NoticeBar,
  Rate, Slider, Switch, Uploader,
  ConfigProvider
} from 'vant'

const app = createApp(App)
const pinia = createPinia()

pinia.use(piniaPluginPersistedstate)

app.use(pinia)
app.use(router)

// Register Vant components
app.use(Button)
app.use(Cell)
app.use(CellGroup)
app.use(Icon)
app.use(Tabbar)
app.use(TabbarItem)
app.use(NavBar)
app.use(Form)
app.use(Field)
app.use(Toast)
app.use(Dialog)
app.use(Loading)
app.use(Swipe)
app.use(SwipeItem)
app.use(Grid)
app.use(GridItem)
app.use(Tag)
app.use(Progress)
app.use(Card)
app.use(Empty)
app.use(Skeleton)
app.use(PullRefresh)
app.use(List)
app.use(Search)
app.use(Badge)
app.use(Popup)
app.use(ActionSheet)
app.use(ShareSheet)
app.use(Checkbox)
app.use(Radio)
app.use(RadioGroup)
app.use(CheckboxGroup)
app.use(Stepper)
app.use(CountDown)
app.use(VanImage)
app.use(Tab)
app.use(Tabs)
app.use(Sticky)
app.use(Divider)
app.use(NoticeBar)
app.use(Rate)
app.use(Slider)
app.use(Switch)
app.use(Uploader)
app.use(ConfigProvider)

app.mount('#app')
