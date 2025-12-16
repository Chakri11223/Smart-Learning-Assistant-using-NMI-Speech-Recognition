import React from 'react';
import { useLocation, Link, Outlet } from 'react-router-dom';
import {
    AppBar,
    Toolbar,
    Typography,
    Container,
    Box,
    Button,
    IconButton,
    Avatar,
    Menu,
    MenuItem,
    ListItemIcon,
    Divider,
    GlobalStyles
} from '@mui/material';
import Settings from '@mui/icons-material/Settings';
import Logout from '@mui/icons-material/Logout';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';

const AppLayout = ({
    authUser,
    themeMode,
    toggleTheme,
    onLogout
}) => {
    const location = useLocation();
    const isVoiceQA = location.pathname === '/voice-qa';
    const [anchorElUser, setAnchorElUser] = React.useState(null);

    const handleOpenUserMenu = (event) => {
        setAnchorElUser(event.currentTarget);
    };

    const handleCloseUserMenu = () => {
        setAnchorElUser(null);
    };

    const handleLogoutClick = () => {
        handleCloseUserMenu();
        onLogout();
    };

    return (
        <>
            <GlobalStyles styles={{ body: { overflowY: 'scroll' } }} />
            <AppBar position="sticky" enableColorOnDark>
                <Toolbar>
                    {authUser && (
                        <Box sx={{ flexGrow: 0, mr: 2 }}>
                            <IconButton
                                onClick={handleOpenUserMenu}
                                sx={{ p: 0 }}
                            >
                                <Avatar sx={{ width: 32, height: 32, bgcolor: '#0ea5e9', fontSize: '0.9rem', fontWeight: 600 }}>
                                    {(authUser?.name?.[0] || authUser?.email?.[0] || '?').toUpperCase()}
                                </Avatar>
                            </IconButton>
                            <Menu
                                sx={{ mt: 1 }}
                                id="menu-appbar"
                                anchorEl={anchorElUser}
                                anchorOrigin={{
                                    vertical: 'bottom',
                                    horizontal: 'left',
                                }}
                                keepMounted
                                transformOrigin={{
                                    vertical: 'top',
                                    horizontal: 'left',
                                }}
                                open={Boolean(anchorElUser)}
                                onClose={handleCloseUserMenu}
                                PaperProps={{
                                    elevation: 0,
                                    sx: {
                                        overflow: 'visible',
                                        filter: 'drop-shadow(0px 2px 8px rgba(0,0,0,0.32))',
                                        mt: 1.5,
                                        minWidth: 200,
                                        '& .MuiAvatar-root': {
                                            width: 32,
                                            height: 32,
                                            ml: -0.5,
                                            mr: 1,
                                        },
                                        '&:before': {
                                            content: '""',
                                            display: 'block',
                                            position: 'absolute',
                                            top: 0,
                                            left: 14,
                                            width: 10,
                                            height: 10,
                                            bgcolor: 'background.paper',
                                            transform: 'translateY(-50%) rotate(45deg)',
                                            zIndex: 0,
                                        },
                                    },
                                }}
                                disableScrollLock={true}
                            >
                                <Box sx={{ px: 2, py: 1.5 }}>
                                    <Typography variant="subtitle1" noWrap sx={{ fontWeight: 600 }}>
                                        {authUser?.name || 'User'}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary" noWrap>
                                        {authUser?.email}
                                    </Typography>
                                </Box>
                                <Divider />
                                <MenuItem component={Link} to="/settings" onClick={handleCloseUserMenu}>
                                    <ListItemIcon>
                                        <Settings fontSize="small" />
                                    </ListItemIcon>
                                    Settings
                                </MenuItem>
                                <MenuItem onClick={handleLogoutClick}>
                                    <ListItemIcon>
                                        <Logout fontSize="small" />
                                    </ListItemIcon>
                                    Logout
                                </MenuItem>
                            </Menu>
                        </Box>
                    )}
                    <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
                        Smart Learning Assistant
                    </Typography>
                    <IconButton
                        aria-label={themeMode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
                        color="inherit"
                        onClick={toggleTheme}
                    >
                        {themeMode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
                    </IconButton>
                    <Link to="/" style={{ textDecoration: 'none', marginRight: '16px' }}>
                        <Button color="inherit" sx={{ fontWeight: 600 }}>
                            Home
                        </Button>
                    </Link>
                    <Link to="/voice-qa" style={{ textDecoration: 'none', marginRight: '16px' }}>
                        <Button color="inherit" sx={{ fontWeight: 600 }}>
                            Voice Q&A
                        </Button>
                    </Link>
                    <Link to="/quiz-generator" style={{ textDecoration: 'none', marginRight: '16px' }}>
                        <Button color="inherit" sx={{ fontWeight: 600 }}>
                            Quiz Generator
                        </Button>
                    </Link>
                    <Link to="/video" style={{ textDecoration: 'none', marginRight: '16px' }}>
                        <Button color="inherit" sx={{ fontWeight: 600 }}>
                            Video
                        </Button>
                    </Link>
                    <Link to="/learning" style={{ textDecoration: 'none', marginRight: '16px' }}>
                        <Button color="inherit" sx={{ fontWeight: 600 }}>
                            Learning Path
                        </Button>
                    </Link>
                    <Link to="/feynman" style={{ textDecoration: 'none', marginRight: '16px' }}>
                        <Button color="inherit" sx={{ fontWeight: 600 }}>
                            Explain & Learn
                        </Button>
                    </Link>

                    <Link to="/analytics" style={{ textDecoration: 'none', marginRight: '16px' }}>
                        <Button color="inherit" sx={{ fontWeight: 600 }}>
                            Analytics
                        </Button>
                    </Link>

                    {!authUser && (
                        <>
                            <Link to="/login" style={{ textDecoration: 'none', marginLeft: '12px' }}>
                                <Button color="inherit" sx={{ fontSize: '14px', fontWeight: 'bold' }}>
                                    Login
                                </Button>
                            </Link>
                            <Link to="/signup" style={{ textDecoration: 'none', marginLeft: '12px' }}>
                                <Button color="secondary" variant="contained" sx={{ fontSize: '14px', fontWeight: 'bold' }}>
                                    Sign Up
                                </Button>
                            </Link>
                        </>
                    )}
                </Toolbar>
            </AppBar>
            {isVoiceQA ? (
                <Outlet />
            ) : (
                <Container maxWidth="xl" sx={{ mt: 3, mb: 3 }}>
                    <Outlet />
                </Container>
            )}
        </>
    );
};

export default AppLayout;
