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

function dragEvent(element,type,dataTransfer,clientY=0){
 const event=new Event(type,{bubbles:true,cancelable:true});
 Object.defineProperties(event,{dataTransfer:{value:dataTransfer},clientY:{value:clientY}});
 fireEvent(element,event);
}
function queueFixture(){
 return ['first','second','third'].map(name=>({path:`C:/${name}.pdf`,name:`${name}.pdf`,size:1024,type:'PDF',range:'',status:'pending',output:`${name}.pdf`}));
}

describe('React desktop workspace',()=>{
 it('offers keep or remove blank pages in advanced settings and saves the choice',async()=>{
  render(<App/>);
  await waitFor(()=>expect(screen.getByRole('button',{name:'最小化'}).disabled).toBe(false));
  fireEvent.click(screen.getByRole('tab',{name:'高级'}));
  const control=screen.getByRole('combobox',{name:'空白页处理'});
  expect(control.value).toBe('keep');
  fireEvent.change(control,{target:{value:'remove'}});
  await waitFor(()=>expect(api.save_config).toHaveBeenCalledWith(expect.objectContaining({blank_page_action:'remove'})));
 });
 it('toggles column sorting and applies the backend order without clearing selection',async()=>{
  state.files=queueFixture();
  render(<App/>);
  const byName=await screen.findByRole('button',{name:'按名称排序'});
  fireEvent.click(screen.getByRole('checkbox',{name:'first.pdf'}));
  api.modify_queue.mockImplementation(async(operation,[direction])=>{
   state={...state,queue_sort:{key:operation.slice(5),direction},files:[...state.files].reverse()};
   return state;
  });
  fireEvent.click(byName);
  await waitFor(()=>expect(byName.closest('th').getAttribute('aria-sort')).toBe('ascending'));
  expect(api.modify_queue).toHaveBeenLastCalledWith('sort_name',['asc']);
  fireEvent.click(byName);
  await waitFor(()=>expect(byName.closest('th').getAttribute('aria-sort')).toBe('descending'));
  expect(api.modify_queue).toHaveBeenLastCalledWith('sort_name',['desc']);
  const byType=screen.getByRole('button',{name:'按类型排序'});
  fireEvent.click(byType);
  await waitFor(()=>expect(byType.closest('th').getAttribute('aria-sort')).toBe('ascending'));
  expect(api.modify_queue).toHaveBeenLastCalledWith('sort_type',['asc']);
  expect(byName.closest('th').getAttribute('aria-sort')).toBe('none');
  expect(screen.getByRole('checkbox',{name:'first.pdf'}).checked).toBe(true);
 });
 it('drags a file tag after another row without showing the external-file overlay',async()=>{
  state.files=queueFixture();
  const {container}=render(<App/>);
  const tag=await screen.findByRole('button',{name:'拖动排序 first.pdf'});
  await waitFor(()=>expect(tag.disabled).toBe(false));
  const row=screen.getByText('third.pdf',{selector:'strong'}).closest('tr');
  vi.spyOn(row,'getBoundingClientRect').mockReturnValue({top:100,height:60,bottom:160});
  const transfer={types:['application/x-matrixflow-queue'],setData:vi.fn()};
  dragEvent(tag,'dragstart',transfer);
  dragEvent(row,'dragover',transfer,150);
  expect(row.classList.contains('insert-after')).toBe(true);
  expect(container.querySelector('.drop-overlay')).toBeNull();
  const reordered={...state,files:[state.files[1],state.files[2],state.files[0]]};
  api.modify_queue.mockResolvedValueOnce(reordered);
  dragEvent(row,'drop',transfer,150);
  await waitFor(()=>expect(api.modify_queue).toHaveBeenCalledWith('move_after',['C:/first.pdf','C:/third.pdf']));
  await waitFor(()=>expect([...container.querySelectorAll('.filename strong')].map(e=>e.textContent)).toEqual(['second.pdf','third.pdf','first.pdf']));
  expect(container.querySelector('.sorting,.insert-after')).toBeNull();
 });
 it('targets the visible row by path when dragging in a filtered queue',async()=>{
  state.files=queueFixture();state.files[1].status='success';
  render(<App/>);
  await screen.findByRole('button',{name:'拖动排序 third.pdf'});
  fireEvent.click(screen.getByRole('button',{name:/^待处理/}));
  expect(screen.queryByText('second.pdf',{selector:'strong'})).toBeNull();
  const tag=screen.getByRole('button',{name:'拖动排序 third.pdf'});
  const row=screen.getByText('first.pdf',{selector:'strong'}).closest('tr');
  vi.spyOn(row,'getBoundingClientRect').mockReturnValue({top:100,height:60,bottom:160});
  const transfer={types:['application/x-matrixflow-queue'],setData:vi.fn()};
  dragEvent(tag,'dragstart',transfer);
  dragEvent(row,'dragover',transfer,110);
  expect(row.classList.contains('insert-before')).toBe(true);
  dragEvent(row,'drop',transfer,110);
  await waitFor(()=>expect(api.modify_queue).toHaveBeenCalledWith('move_before',['C:/third.pdf','C:/first.pdf']));
 });
 it('cancels an unfinished drag and still recognizes external file drops',async()=>{
  state.files=queueFixture();
  const {container}=render(<App/>);
  const tag=await screen.findByRole('button',{name:'拖动排序 first.pdf'});
  const transfer={types:['application/x-matrixflow-queue'],setData:vi.fn()};
  dragEvent(tag,'dragstart',transfer);
  dragEvent(tag,'dragend',transfer);
  expect(container.querySelector('.sorting')).toBeNull();
  expect(api.modify_queue).not.toHaveBeenCalled();
  dragEvent(container.querySelector('.app-shell'),'dragover',{types:['Files']});
  expect(container.querySelector('.drop-overlay')).not.toBeNull();
 });
 it('disables file dragging while converting',async()=>{
  state.files=queueFixture();state.busy=true;
  render(<App/>);
  const tag=await screen.findByRole('button',{name:'拖动排序 first.pdf'});
  expect(tag.disabled).toBe(true);
  expect(tag.draggable).toBe(false);
  expect(screen.getByRole('button',{name:'按名称排序'}).disabled).toBe(true);
  expect(screen.getByRole('button',{name:'按类型排序'}).disabled).toBe(true);
  dragEvent(tag,'dragstart',{types:[],setData:vi.fn()});
  expect(api.modify_queue).not.toHaveBeenCalled();
 });
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
