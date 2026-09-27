import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup,act} from '@testing-library/react';
import {App} from './src/main';

const defaults={engine:'auto',lang:'zh_cn',matrix_motion:false,out_mode:'original',output_dir:'',naming_tpl:'{name}',wm1_text:'',wm1_pos:'None',wm2_text:'',wm2_pos:'None',wm_font:'',wm_size:60,wm_color:'#C0C0C0',wm_alpha:.3,pg_enabled:false,pg_pos:'bc',pg_format:'- {n} / {total} -',merge_all:false,password:''};
let state,api;
beforeEach(()=>{
 state={files:[],busy:false,progress:0,maximum:1,label:'',logs:[],last_output:'',actual_engine:'',presets:[],fonts:[],positions:[],translations:{},config:defaults};
 api={snapshot:vi.fn(async()=>state),save_config:vi.fn(async c=>c),window_control:vi.fn(async action=>action==='maximize'),modify_queue:vi.fn(async()=>({...state,files:[]})),preset:vi.fn(async()=>state)};
 window.pywebview={api};
 window.matchMedia=()=>({matches:false});
 global.ResizeObserver=class{observe(){}disconnect(){}};
 HTMLCanvasElement.prototype.getContext=()=>({fillRect(){},fillText(){}});
});
afterEach(()=>{cleanup();delete window.pywebview;vi.restoreAllMocks()});

describe('React desktop workspace',()=>{
 it('waits for injected methods instead of calling the empty bridge object',async()=>{
  window.pywebview={api:{}};
  render(<App/>);
  expect(screen.getByRole('button',{name:'最小化'}).disabled).toBe(true);
  expect(screen.queryByText(/snapshot.*not a function/)).toBeNull();
  state.files=[{path:'C:/ready.pdf',name:'ready.pdf',size:1024,type:'PDF',range:'',status:'pending',output:'ready.pdf'}];
  await act(async()=>{
   window.pywebview.api=api;
   window.dispatchEvent(new Event('pywebviewready'));
   window.dispatchEvent(new Event('pywebviewready'));
  });
  expect(await screen.findByText('ready.pdf',{selector:'strong'})).toBeTruthy();
  expect(screen.getByRole('button',{name:'最小化'}).disabled).toBe(false);
  expect(api.snapshot).toHaveBeenCalledTimes(1);
 });
 it('recovers when the bridge appears after mounting without a ready event',async()=>{
  delete window.pywebview;
  render(<App/>);
  window.pywebview={api};
  await waitFor(()=>expect(screen.getByRole('button',{name:'最小化'}).disabled).toBe(false));
  expect(screen.queryByText(/not a function/)).toBeNull();
 });
 it('handles actions during bridge injection without a JavaScript error',async()=>{
  window.pywebview={api:{}};
  render(<App/>);
  fireEvent.click(screen.getByRole('button',{name:'添加文件'}));
  expect(await screen.findByText('正在连接桌面服务，请稍候')).toBeTruthy();
  expect(screen.queryByText(/not a function/)).toBeNull();
 });
 it('connects and shows the empty queue without decorative header controls',async()=>{
  render(<App/>);
  await waitFor(()=>expect(screen.getByRole('button',{name:'最小化'}).disabled).toBe(false));
  expect(screen.getByText('文件就位，即刻开始')).toBeTruthy();
  expect(screen.queryByText('离线处理')).toBeNull();
  expect(screen.queryByRole('button',{name:'动态代码雨'})).toBeNull();
  expect(screen.getByRole('button',{name:'开始转换'}).disabled).toBe(true);
 });
 it('routes all titlebar controls and switches maximize to restore',async()=>{
  render(<App/>);
  await waitFor(()=>expect(screen.getByRole('button',{name:'最小化'}).disabled).toBe(false));
  fireEvent.click(screen.getByRole('button',{name:'最小化'}));
  fireEvent.click(screen.getByRole('button',{name:'最大化'}));
  await screen.findByRole('button',{name:'还原'});
  fireEvent.click(screen.getByRole('button',{name:'关闭窗口'}));
  expect(api.window_control.mock.calls.map(c=>c[0])).toEqual(['minimize','maximize','close']);
 });
 it('renders real queue data and removes the selected file',async()=>{
  state.files=[{path:'C:/sample.docx',name:'sample.docx',size:2048,type:'Word',range:'',status:'pending',output:'sample.pdf'}];
  render(<App/>);
  expect(await screen.findByText('sample.docx')).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'删除 sample.docx'}));
  await waitFor(()=>expect(api.modify_queue).toHaveBeenCalledWith('remove',['C:/sample.docx']));
 });
 it('switches settings tabs and retains the code-rain control in preferences',async()=>{
  render(<App/>);
  await waitFor(()=>expect(api.snapshot).toHaveBeenCalled());
  fireEvent.click(screen.getByRole('tab',{name:'水印'}));
  expect(screen.getByText('水印文字 01')).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'偏好设置'}));
  expect(screen.getByRole('switch',{name:'动态代码雨'})).toBeTruthy();
 });
});
