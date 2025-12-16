import React from 'react';
import {
    Container,
    Typography,
    Paper,
    Box,
    Switch,
    List,
    ListItem,
    ListItemText,
    ListItemSecondaryAction,
    Divider,
    Avatar,
    Stack,
    ToggleButton,
    ToggleButtonGroup,
    useTheme
} from '@mui/material';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import NotificationsIcon from '@mui/icons-material/Notifications';
import PersonIcon from '@mui/icons-material/Person';
import TextFormatIcon from '@mui/icons-material/TextFormat';

const Settings = ({ authUser, themeMode, toggleTheme, fontSize, setFontSize }) => {
    const theme = useTheme();

    const handleFontSizeChange = (event, newSize) => {
        if (newSize !== null) {
            setFontSize(newSize);
        }
    };

    return (
        <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
            <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold', mb: 4, color: 'primary.main' }}>
                Settings
            </Typography>

            {/* Profile Section */}
            <Paper elevation={0} sx={{ p: 3, mb: 3, borderRadius: 4, border: '1px solid', borderColor: 'divider' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <PersonIcon color="primary" sx={{ mr: 1.5 }} />
                    <Typography variant="h6" fontWeight="bold">
                        Profile
                    </Typography>
                </Box>
                <Divider sx={{ mb: 3 }} />

                <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                    <Avatar
                        sx={{
                            width: 80,
                            height: 80,
                            bgcolor: 'primary.main',
                            fontSize: '2rem',
                            fontWeight: 'bold'
                        }}
                    >
                        {(authUser?.name?.[0] || authUser?.email?.[0] || '?').toUpperCase()}
                    </Avatar>
                    <Box>
                        <Typography variant="h6" gutterBottom>
                            {authUser?.name || 'User'}
                        </Typography>
                        <Typography variant="body1" color="text.secondary">
                            {authUser?.email}
                        </Typography>
                        <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'success.main', fontWeight: 'bold' }}>
                            {authUser?.verified ? 'Verified Account' : 'Unverified'}
                        </Typography>
                    </Box>
                </Box>
            </Paper>

            {/* Appearance Section */}
            <Paper elevation={0} sx={{ p: 3, mb: 3, borderRadius: 4, border: '1px solid', borderColor: 'divider' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    {themeMode === 'dark' ? <DarkModeIcon color="primary" sx={{ mr: 1.5 }} /> : <LightModeIcon color="primary" sx={{ mr: 1.5 }} />}
                    <Typography variant="h6" fontWeight="bold">
                        Appearance
                    </Typography>
                </Box>
                <Divider sx={{ mb: 2 }} />

                <List disablePadding>
                    <ListItem disableGutters>
                        <ListItemText
                            primary="Dark Mode"
                            secondary="Switch between light and dark themes"
                        />
                        <ListItemSecondaryAction>
                            <Switch
                                edge="end"
                                onChange={toggleTheme}
                                checked={themeMode === 'dark'}
                                color="primary"
                            />
                        </ListItemSecondaryAction>
                    </ListItem>

                    <Divider component="li" sx={{ my: 2 }} />

                    <ListItem disableGutters sx={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', mb: 2 }}>
                            <ListItemText
                                primary="Font Size"
                                secondary="Adjust the text size for better readability"
                            />
                            <TextFormatIcon color="action" />
                        </Box>
                        <Box sx={{ width: '100%', display: 'flex', justifyContent: 'center' }}>
                            <ToggleButtonGroup
                                value={fontSize}
                                exclusive
                                onChange={handleFontSizeChange}
                                aria-label="font size"
                                fullWidth
                                sx={{ maxWidth: 400 }}
                            >
                                <ToggleButton value="small" aria-label="small font">
                                    Small
                                </ToggleButton>
                                <ToggleButton value="medium" aria-label="medium font">
                                    Medium
                                </ToggleButton>
                                <ToggleButton value="large" aria-label="large font">
                                    Large
                                </ToggleButton>
                            </ToggleButtonGroup>
                        </Box>
                    </ListItem>
                </List>
            </Paper>

            {/* Notifications Section (Placeholder) */}
            <Paper elevation={0} sx={{ p: 3, mb: 3, borderRadius: 4, border: '1px solid', borderColor: 'divider' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <NotificationsIcon color="primary" sx={{ mr: 1.5 }} />
                    <Typography variant="h6" fontWeight="bold">
                        Notifications
                    </Typography>
                </Box>
                <Divider sx={{ mb: 2 }} />

                <List disablePadding>
                    <ListItem disableGutters>
                        <ListItemText
                            primary="Email Notifications"
                            secondary="Receive updates about your learning path"
                        />
                        <ListItemSecondaryAction>
                            <Switch edge="end" defaultChecked color="primary" />
                        </ListItemSecondaryAction>
                    </ListItem>
                </List>
            </Paper>

            <Typography variant="caption" display="block" align="center" color="text.secondary" sx={{ mt: 4 }}>
                Smart Learning Assistant v1.0.0
            </Typography>
        </Container>
    );
};

export default Settings;
