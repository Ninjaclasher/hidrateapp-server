from django.urls import include, path

from hidrateapp import views

urlpatterns = [
    path('', views.home, name='hidrateapp_home'),
    path('parse/', include([
        path('config', views.Config.as_view()),
        path('users', views.Classes.UserView.as_view()),
        path('users/', include([
            path('', views.Classes.UserView.as_view()),
            path('<id>', views.Classes.DetailUserView.as_view()),
        ])),
        path('login', views.LoginView.as_view()),
        path('logout', views.LogoutView.as_view()),
        path('events/', include([
            path('AppOpened', views.empty),
            path('setManualGoal', views.empty),
            path('viewPreviousDay', views.empty),
            path('previousDay', views.empty),
            path('addBottle', views.empty),
            path('unpairBottle', views.empty),
            path('logout', views.empty),
        ])),
        path('functions/', include([
            path('userexists/', views.Functions.UserExists.as_view()),
            path('canaddbottle', views.Functions.CanAddBottle.as_view()),
            path('getmyglows', views.Functions.ListGlow.as_view()),
            path('saveglow', views.Functions.CreateGlow.as_view()),
            path('deleteglow', views.Functions.DeleteGlow.as_view()),
            path('calculatedaytotal', views.Functions.CalculateDayTotal.as_view()),

            path('listfirmware', views.empty),
            path('getuserads', views.empty),
            path('getusergroups', views.empty),
            path('getmyfriends', views.empty),
            path('getmyawards', views.empty),
            path('getmychallenges', views.empty),
            path('getclosedchallenges', views.empty),
            path('getjoinablechallenges', views.empty),
            path('trophyanalytics', views.empty),
        ])),
        path('classes/', include([
            path('_Installation', views.Classes.InstallationView.as_view()),
            path('_Installation/', include([
                path('', views.Classes.InstallationView.as_view()),
                path('<id>', views.Classes.DetailInstallationView.as_view()),
            ])),
            path('_User', views.Classes.UserView.as_view()),
            path('_User/', include([
                path('', views.Classes.UserView.as_view()),
                path('<id>', views.Classes.DetailUserView.as_view()),
            ])),
            path('Sip', views.Classes.SipView.as_view()),
            path('Sip/', include([
                path('', views.Classes.SipView.as_view()),
                path('<id>', views.Classes.DetailSipView.as_view()),
            ])),
            path('Bottle', views.Classes.BottleView.as_view()),
            path('Bottle/', include([
                path('', views.Classes.BottleView.as_view()),
                path('<id>', views.Classes.DetailBottleView.as_view()),
            ])),
            path('Location', views.Classes.LocationView.as_view()),
            path('Location/', include([
                path('', views.Classes.LocationView.as_view()),
                path('<id>', views.Classes.DetailLocationView.as_view()),
            ])),
            path('Day', views.Classes.DayView.as_view()),
            path('Day/', include([
                path('', views.Classes.DayView.as_view()),
                path('<id>', views.Classes.DetailDayView.as_view()),
            ])),
            path('UserHealthStats', views.Classes.UserHealthStats.as_view()),
            path('UserHealthStats/', include([
                path('<id>', views.Classes.DetailUserHealthStats.as_view()),
            ])),
        ])),
    ])),
]
