import {
  ArrowRightFromSquare,
  Bars,
  Clock,
  Gear,
  House,
  Persons,
} from '@gravity-ui/icons';
import {
  Avatar,
  Button,
  Drawer,
  Dropdown,
  Header,
  Label,
  useOverlayState,
} from '@heroui/react';
import type { ReactNode } from 'react';

export type ViewId = 'home' | 'accounts' | 'activity' | 'settings';

const NAV_ITEMS: Array<{
  id: ViewId;
  label: string;
  icon: typeof House;
}> = [
  { id: 'home', label: '首页', icon: House },
  { id: 'accounts', label: '账号', icon: Persons },
  { id: 'activity', label: '活动', icon: Clock },
  { id: 'settings', label: '设置', icon: Gear },
];

function Logo() {
  return (
    <div className="flex items-center gap-2">
      <img
        src="/logo.png"
        alt="FastLogin"
        className="size-8 rounded-lg object-contain"
      />
      <span className="text-base font-bold">FastLogin</span>
    </div>
  );
}

function NavItems({
  view,
  onViewChange,
  onNavigate,
  items,
}: {
  view: ViewId;
  onViewChange: (view: ViewId) => void;
  onNavigate?: () => void;
  items: typeof NAV_ITEMS;
}) {
  return (
    <>
      {items.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          type="button"
          className="nav-link"
          data-active={view === id}
          aria-current={view === id ? 'page' : undefined}
          onClick={() => {
            onViewChange(id);
            onNavigate?.();
          }}
        >
          <Icon aria-hidden="true" className="size-4 shrink-0" />
          <span>{label}</span>
        </button>
      ))}
    </>
  );
}

export function AppShell({
  view,
  onViewChange,
  username = 'admin',
  onLogout,
  logoutBusy,
  children,
}: {
  view: ViewId;
  onViewChange: (view: ViewId) => void;
  username?: string;
  onLogout?: () => void;
  logoutBusy?: boolean;
  children: ReactNode;
}) {
  const drawer = useOverlayState();

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b border-separator bg-background/90 backdrop-blur">
        <div className="flex w-full items-center justify-between gap-4 px-4 py-2.5 md:px-6">
          <div className="flex items-center gap-4">
            <Button
              isIconOnly
              variant="tertiary"
              size="sm"
              aria-label="打开菜单"
              className="lg:hidden"
              onPress={drawer.open}
            >
              <Bars aria-hidden="true" />
            </Button>
            <Logo />
          </div>

          <nav
            className="hidden items-center gap-1 lg:flex"
            aria-label="主导航"
          >
            <NavItems
              view={view}
              onViewChange={onViewChange}
              items={NAV_ITEMS}
            />
          </nav>

          <div className="flex items-center gap-2">
            <Dropdown>
              <Button
                isIconOnly
                variant="tertiary"
                aria-label={`用户菜单：${username}`}
              >
                <Avatar className="size-7">
                  <Avatar.Fallback className="text-xs">
                    {username.slice(0, 2).toUpperCase()}
                  </Avatar.Fallback>
                </Avatar>
              </Button>
              <Dropdown.Popover placement="bottom end">
                <Dropdown.Menu
                  onAction={(key) => {
                    if (key === 'logout' && onLogout) {
                      onLogout();
                    }
                  }}
                >
                  <Dropdown.Section>
                    <Header>{username}</Header>
                    <Dropdown.Item id="logout" textValue="退出登录">
                      <ArrowRightFromSquare
                        className="size-4 shrink-0 text-muted"
                        aria-hidden="true"
                      />
                      <Label>退出登录</Label>
                    </Dropdown.Item>
                  </Dropdown.Section>
                </Dropdown.Menu>
              </Dropdown.Popover>
            </Dropdown>
          </div>
        </div>
      </header>

      <Drawer.Backdrop
        isOpen={drawer.isOpen}
        onOpenChange={drawer.setOpen}
        isDismissable
      >
        <Drawer.Content placement="left">
          <Drawer.Dialog>
            <Drawer.CloseTrigger />
            <Drawer.Header>
              <Drawer.Heading>菜单</Drawer.Heading>
            </Drawer.Header>
            <Drawer.Body>
              <nav className="flex flex-col gap-1" aria-label="移动导航">
                <NavItems
                  view={view}
                  onViewChange={onViewChange}
                  onNavigate={drawer.close}
                  items={NAV_ITEMS}
                />
              </nav>
            </Drawer.Body>
            <Drawer.Footer className="flex items-center justify-between">
              <span className="text-sm text-muted">{username}</span>
              <Button
                size="sm"
                variant="danger-soft"
                isDisabled={logoutBusy}
                onPress={() => {
                  drawer.close();
                  onLogout?.();
                }}
              >
                <ArrowRightFromSquare aria-hidden="true" />
                退出
              </Button>
            </Drawer.Footer>
          </Drawer.Dialog>
        </Drawer.Content>
      </Drawer.Backdrop>

      <main className="mx-auto max-w-6xl px-4 py-6 md:px-6 md:py-8">
        <div key={view} className="page-enter">
          {children}
        </div>
      </main>
    </div>
  );
}
